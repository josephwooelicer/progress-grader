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
from app.models.git_event import GitEvent
from app.models.project import RubricDimension
from app.models.rubric import RubricScore, TimelineComment, TimelineFlag
from app.models.user import User

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


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
