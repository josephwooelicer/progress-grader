"""Teacher API: timeline, comments, flags, rubric grading, CSV export."""
import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import TeacherUser
from app.models.conversation import ConversationMessage
from app.models.consent import Consent
from app.models.git_event import GitEvent
from app.models.project import Course, Project, RubricDimension
from app.models.rubric import RubricScore, TimelineComment, TimelineFlag
from app.models.user import User
from app.models.workspace import Workspace

router = APIRouter(prefix="/api/teacher", tags=["teacher"])

_MANDATORY_DIMENSIONS = [
    ("Prompt quality",        "Clarity, specificity, and context given in prompts",              "Score 5 if prompts are consistently clear and well-scoped. Score 3 for adequate prompts with some vagueness. Score 1 for unclear or context-free prompts.",         5, 0),
    ("Problem decomposition", "Whether the student breaks problems into small, focused asks",     "Score 5 if the student consistently decomposes problems. Score 3 for occasional decomposition. Score 1 if the student asks for everything in one prompt.",           5, 1),
    ("Context management",    "Appropriate use of new conversations to prevent context bloat",   "Score 5 if conversation boundaries are used strategically. Score 3 for some awareness. Score 1 if student never starts new conversations.",                         5, 2),
    ("Spec-driven approach",  "Evidence of writing specs or plans before asking for code",       "Score 5 if specs/plans are written first consistently. Score 3 for occasional planning. Score 1 if code is always requested without prior planning.",                5, 3),
    ("Commit granularity",    "Small, logical commits with clear messages",                      "Score 5 if commits are atomic and well-described. Score 3 for average commit size/messages. Score 1 for infrequent or poorly described commits.",                    5, 4),
    ("Branching strategy",    "Feature branches, meaningful names, PR usage",                    "Score 5 if branches are used consistently with meaningful names and PRs. Score 3 for some branching. Score 1 if everything is committed directly to main.",           5, 5),
    ("PR quality",            "PR descriptions, review engagement",                              "Score 5 if PRs have clear descriptions and engage with review. Score 3 for minimal descriptions. Score 1 if PRs are empty or absent.",                              5, 6),
]


# ── Courses ──────────────────────────────────────────────────────────────────

@router.get("/courses")
async def list_courses(
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Course).order_by(Course.name))
    courses = result.scalars().all()
    return {
        "courses": [
            {"id": str(c.id), "name": c.name, "slug": c.slug, "gitea_org": c.gitea_org, "created_at": c.created_at.isoformat()}
            for c in courses
        ]
    }


class CreateCourseRequest(BaseModel):
    name: str
    slug: str


@router.post("/courses", status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CreateCourseRequest,
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(select(Course).where(Course.slug == body.slug))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Slug already in use")
    course = Course(id=uuid.uuid4(), name=body.name, slug=body.slug)
    db.add(course)
    await db.commit()
    return {"id": str(course.id), "name": course.name, "slug": course.slug}


class CreateProjectRequest(BaseModel):
    name: str
    slug: str
    description: str | None = None
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    skeleton_files: dict | None = None


@router.post("/courses/{course_id}/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    course_id: uuid.UUID,
    body: CreateProjectRequest,
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")

    api_key_encrypted: str | None = None
    if body.api_key:
        from cryptography.fernet import Fernet
        from app.config import settings
        api_key_encrypted = Fernet(settings.encryption_key.encode()).encrypt(body.api_key.encode()).decode()

    project = Project(
        id=uuid.uuid4(),
        course_id=course_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        provider=body.provider,
        model=body.model,
        api_key_encrypted=api_key_encrypted,
        skeleton_files=body.skeleton_files,
    )
    db.add(project)
    await db.flush()

    # Insert mandatory rubric dimensions
    for i, (name, desc, criteria, max_score, order) in enumerate(_MANDATORY_DIMENSIONS):
        db.add(RubricDimension(
            id=uuid.uuid4(),
            project_id=project.id,
            name=name,
            description=desc,
            scoring_criteria=criteria,
            max_score=max_score,
            is_mandatory=True,
            display_order=order,
        ))

    await db.commit()
    return {"id": str(project.id), "name": project.name, "slug": project.slug}


@router.get("/courses/{course_id}/students")
async def list_course_students(
    course_id: uuid.UUID,
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    """Return all students with workspaces in this course, with consent status."""
    projects_result = await db.execute(
        select(Project).where(Project.course_id == course_id)
    )
    projects = projects_result.scalars().all()

    rows = []
    for project in projects:
        workspaces_result = await db.execute(
            select(Workspace).where(Workspace.project_id == project.id)
        )
        for ws in workspaces_result.scalars().all():
            student = await db.get(User, ws.student_id)
            if not student or student.deleted_at:
                continue
            consent = await db.scalar(
                select(Consent).where(
                    Consent.student_id == ws.student_id,
                    Consent.project_id == project.id,
                    Consent.revoked_at.is_(None),
                )
            )
            rows.append({
                "id": str(student.id),
                "name": student.name,
                "email": student.email,
                "project_id": str(project.id),
                "project_name": project.name,
                "consented": consent is not None,
            })

    return {"students": rows}


# ── Rubric dimensions ─────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/rubric/dimensions")
async def list_rubric_dimensions(
    project_id: uuid.UUID,
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RubricDimension).where(RubricDimension.project_id == project_id)
        .order_by(RubricDimension.display_order)
    )
    dims = result.scalars().all()
    return {
        "dimensions": [
            {
                "id": str(d.id),
                "project_id": str(d.project_id),
                "name": d.name,
                "description": d.description,
                "scoring_criteria": d.scoring_criteria,
                "max_score": d.max_score,
                "is_mandatory": d.is_mandatory,
                "display_order": d.display_order,
            }
            for d in dims
        ]
    }


class CreateDimensionRequest(BaseModel):
    name: str
    description: str
    scoring_criteria: str
    max_score: int = 5


@router.post("/projects/{project_id}/rubric/dimensions", status_code=status.HTTP_201_CREATED)
async def create_rubric_dimension(
    project_id: uuid.UUID,
    body: CreateDimensionRequest,
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    # Find highest current display_order
    result = await db.execute(
        select(RubricDimension).where(RubricDimension.project_id == project_id)
        .order_by(RubricDimension.display_order.desc())
    )
    dims = result.scalars().all()
    next_order = (dims[0].display_order + 1) if dims else 0

    dim = RubricDimension(
        id=uuid.uuid4(),
        project_id=project_id,
        name=body.name,
        description=body.description,
        scoring_criteria=body.scoring_criteria,
        max_score=body.max_score,
        is_mandatory=False,
        display_order=next_order,
    )
    db.add(dim)
    await db.commit()
    return {
        "id": str(dim.id),
        "name": dim.name,
        "description": dim.description,
        "scoring_criteria": dim.scoring_criteria,
        "max_score": dim.max_score,
        "is_mandatory": False,
        "display_order": dim.display_order,
    }


@router.delete("/projects/{project_id}/rubric/dimensions/{dimension_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rubric_dimension(
    project_id: uuid.UUID,
    dimension_id: uuid.UUID,
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    dim = await db.get(RubricDimension, dimension_id)
    if not dim or dim.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dimension not found")
    if dim.is_mandatory:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot delete mandatory dimensions")
    await db.delete(dim)
    await db.commit()


@router.get("/projects/{project_id}/rubric/scores")
async def get_rubric_scores(
    project_id: uuid.UUID,
    student_id: uuid.UUID,
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RubricScore).where(
            RubricScore.project_id == project_id,
            RubricScore.student_id == student_id,
            RubricScore.teacher_id == current_user.id,
        )
    )
    scores = result.scalars().all()
    return {
        "scores": [
            {
                "id": str(s.id),
                "dimension_id": str(s.dimension_id),
                "student_id": str(s.student_id),
                "suggested_score": s.suggested_score,
                "suggested_justification": s.suggested_justification,
                "confirmed_score": s.confirmed_score,
                "confirmed_justification": s.confirmed_justification,
            }
            for s in scores
        ]
    }


# ── Timeline ────────────────────────────────────────────────────────────────

@router.get("/students/{student_id}/projects/{project_id}/timeline")
async def get_timeline(
    student_id: uuid.UUID,
    project_id: uuid.UUID,
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    messages_result = await db.execute(
        select(ConversationMessage).where(
            ConversationMessage.student_id == student_id,
            ConversationMessage.project_id == project_id,
        ).order_by(ConversationMessage.created_at)
    )
    messages = messages_result.scalars().all()

    events_result = await db.execute(
        select(GitEvent).where(
            GitEvent.student_id == student_id,
            GitEvent.project_id == project_id,
        ).order_by(GitEvent.created_at)
    )
    events = events_result.scalars().all()

    timeline = []
    for m in messages:
        timeline.append({
            "type": "conversation_message",
            "id": str(m.id),
            "conversation_id": str(m.conversation_id),
            "role": m.role,
            "content": m.content,
            "model": m.model,
            "input_tokens": m.input_tokens,
            "output_tokens": m.output_tokens,
            "created_at": m.created_at.isoformat(),
        })
    for e in events:
        timeline.append({
            "type": "git_event",
            "id": str(e.id),
            "event_type": e.event_type,
            "commit_sha": e.commit_sha,
            "commit_message": e.commit_message,
            "branch_name": e.branch_name,
            "pr_number": e.pr_number,
            "pr_title": e.pr_title,
            "forced": e.forced,
            "created_at": e.created_at.isoformat(),
        })

    timeline.sort(key=lambda x: x["created_at"])
    return {"timeline": timeline}


# ── Comments ─────────────────────────────────────────────────────────────────

class CommentRequest(BaseModel):
    student_id: uuid.UUID
    project_id: uuid.UUID
    entry_type: str  # conversation_message | git_event
    entry_id: uuid.UUID
    content: str


@router.post("/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(
    body: CommentRequest,
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    comment = TimelineComment(
        id=uuid.uuid4(),
        teacher_id=current_user.id,
        student_id=body.student_id,
        project_id=body.project_id,
        entry_type=body.entry_type,
        entry_id=body.entry_id,
        content=body.content,
    )
    db.add(comment)
    await db.commit()
    return {"id": str(comment.id)}


# ── Flags ────────────────────────────────────────────────────────────────────

class FlagRequest(BaseModel):
    student_id: uuid.UUID
    project_id: uuid.UUID
    entry_type: str
    entry_id: uuid.UUID
    note: str | None = None


@router.post("/flags/toggle", status_code=status.HTTP_200_OK)
async def toggle_flag(
    body: FlagRequest,
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(
        select(TimelineFlag).where(
            TimelineFlag.teacher_id == current_user.id,
            TimelineFlag.entry_type == body.entry_type,
            TimelineFlag.entry_id == body.entry_id,
        )
    )
    if existing:
        await db.delete(existing)
        await db.commit()
        return {"flagged": False}

    flag = TimelineFlag(
        id=uuid.uuid4(),
        teacher_id=current_user.id,
        student_id=body.student_id,
        project_id=body.project_id,
        entry_type=body.entry_type,
        entry_id=body.entry_id,
        note=body.note,
    )
    db.add(flag)
    await db.commit()
    return {"flagged": True, "id": str(flag.id)}


# ── Rubric grading ────────────────────────────────────────────────────────────

class GradeRequest(BaseModel):
    student_id: uuid.UUID
    dimension_id: uuid.UUID
    confirmed_score: int
    confirmed_justification: str | None = None


@router.post("/projects/{project_id}/rubric/grade")
async def save_rubric_grade(
    project_id: uuid.UUID,
    body: GradeRequest,
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(
        select(RubricScore).where(
            RubricScore.student_id == body.student_id,
            RubricScore.project_id == project_id,
            RubricScore.dimension_id == body.dimension_id,
            RubricScore.teacher_id == current_user.id,
        )
    )
    if existing:
        existing.confirmed_score = body.confirmed_score
        existing.confirmed_justification = body.confirmed_justification
    else:
        db.add(RubricScore(
            id=uuid.uuid4(),
            student_id=body.student_id,
            project_id=project_id,
            dimension_id=body.dimension_id,
            teacher_id=current_user.id,
            confirmed_score=body.confirmed_score,
            confirmed_justification=body.confirmed_justification,
        ))
    await db.commit()
    return {"ok": True}


@router.post("/projects/{project_id}/rubric/ai-suggest")
async def ai_suggest_grades(
    project_id: uuid.UUID,
    student_id: uuid.UUID,
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    """Ask AI to suggest rubric scores for a student."""
    from app.services.grading_service import build_grading_context, request_ai_grading

    dimensions_result = await db.execute(
        select(RubricDimension).where(RubricDimension.project_id == project_id)
        .order_by(RubricDimension.display_order)
    )
    dimensions = [
        {"name": d.name, "description": d.description, "scoring_criteria": d.scoring_criteria, "max_score": d.max_score}
        for d in dimensions_result.scalars().all()
    ]

    messages_result = await db.execute(
        select(ConversationMessage).where(
            ConversationMessage.student_id == student_id,
            ConversationMessage.project_id == project_id,
        ).order_by(ConversationMessage.created_at)
    )
    messages = [
        {"created_at": m.created_at.isoformat(), "role": m.role, "content": m.content}
        for m in messages_result.scalars().all()
    ]

    events_result = await db.execute(
        select(GitEvent).where(
            GitEvent.student_id == student_id,
            GitEvent.project_id == project_id,
        ).order_by(GitEvent.created_at)
    )
    events = [
        {
            "created_at": e.created_at.isoformat(),
            "event_type": e.event_type,
            "commit_message": e.commit_message,
            "pr_title": e.pr_title,
            "branch_name": e.branch_name,
            "forced": e.forced,
        }
        for e in events_result.scalars().all()
    ]

    prompt = await build_grading_context(student_id, project_id, dimensions, messages, events)
    suggestions = await request_ai_grading(prompt)

    # Store suggestions (don't overwrite confirmed scores)
    dims_by_name = {d["name"]: d for d in dimensions}
    dim_rows_result = await db.execute(
        select(RubricDimension).where(RubricDimension.project_id == project_id)
    )
    dim_rows = {d.name: d for d in dim_rows_result.scalars().all()}

    for sug in suggestions:
        dim_row = dim_rows.get(sug["dimension_name"])
        if not dim_row:
            continue
        existing = await db.scalar(
            select(RubricScore).where(
                RubricScore.student_id == student_id,
                RubricScore.project_id == project_id,
                RubricScore.dimension_id == dim_row.id,
                RubricScore.teacher_id == current_user.id,
            )
        )
        if existing:
            existing.suggested_score = sug["score"]
            existing.suggested_justification = sug["justification"]
        else:
            db.add(RubricScore(
                id=uuid.uuid4(),
                student_id=student_id,
                project_id=project_id,
                dimension_id=dim_row.id,
                teacher_id=current_user.id,
                suggested_score=sug["score"],
                suggested_justification=sug["justification"],
            ))
    await db.commit()
    return {"suggestions": suggestions}


# ── CSV Export ────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/rubric/export.csv")
async def export_rubric_csv(
    project_id: uuid.UUID,
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    dimensions_result = await db.execute(
        select(RubricDimension).where(RubricDimension.project_id == project_id)
        .order_by(RubricDimension.display_order)
    )
    dimensions = dimensions_result.scalars().all()

    scores_result = await db.execute(
        select(RubricScore, User).join(User, RubricScore.student_id == User.id).where(
            RubricScore.project_id == project_id,
            RubricScore.teacher_id == current_user.id,
        )
    )
    rows = scores_result.all()

    # Group by student
    student_scores: dict[str, dict] = {}
    for score, user in rows:
        sid = str(score.student_id)
        if sid not in student_scores:
            student_scores[sid] = {"name": user.name, "email": user.email, "scores": {}}
        student_scores[sid]["scores"][str(score.dimension_id)] = score.confirmed_score

    dim_ids = [str(d.id) for d in dimensions]
    dim_names = [d.name for d in dimensions]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student Name", "Email"] + dim_names + ["Total"])

    for sid, data in student_scores.items():
        row_scores = [data["scores"].get(did) for did in dim_ids]
        total = sum(s for s in row_scores if s is not None)
        writer.writerow([data["name"], data["email"]] + row_scores + [total])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=rubric-{project_id}.csv"},
    )
