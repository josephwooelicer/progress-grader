"""Workspace router: create, pause, resume, reset, destroy."""
import secrets
import uuid
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import StudentUser, TeacherUser
from app.models.project import Project
from app.models.workspace import Workspace
from app.services import gitea_client, workspace_service

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


def _fernet() -> Fernet:
    return Fernet(settings.encryption_key.encode())


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


class WorkspaceActionRequest(BaseModel):
    project_id: uuid.UUID


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: WorkspaceActionRequest,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    # Idempotent — return existing if already created
    existing = await db.scalar(
        select(Workspace).where(
            Workspace.student_id == current_user.id,
            Workspace.project_id == body.project_id,
        )
    )
    if existing and existing.state not in ("destroyed",):
        return {"workspace_id": str(existing.id), "url": existing.url, "state": existing.state}

    project = await db.get(Project, body.project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    workspace = Workspace(
        id=uuid.uuid4(),
        student_id=current_user.id,
        project_id=body.project_id,
        state="pending",
    )
    db.add(workspace)
    await db.flush()

    # Set up Gitea repo
    course = await db.get(__import__("app.models.project", fromlist=["Course"]).Course, project.course_id)
    org = course.gitea_org if course and course.gitea_org else "progress-grader"
    repo_name = f"{current_user.gitea_username or str(current_user.id)}-{project.slug}"

    await gitea_client.create_repo(org, repo_name)
    if current_user.gitea_username:
        await gitea_client.add_collaborator(org, repo_name, current_user.gitea_username)

    # Register webhook
    webhook_secret = secrets.token_hex(32)
    await gitea_client.register_webhook(
        org, repo_name,
        f"{settings.backend_url}/webhooks/gitea",
        webhook_secret,
    )

    # Push skeleton files
    skeleton: dict = project.skeleton_files or {}
    if skeleton:
        await gitea_client.initial_commit(org, repo_name, skeleton)

    # Generate student Gitea token
    token_name = f"workspace-{workspace.id}"
    if current_user.gitea_username:
        raw_token = await gitea_client.create_user_token(current_user.gitea_username, token_name)
        workspace.gitea_token_encrypted = _encrypt(raw_token)

    # Start container
    container_id, url = workspace_service.create_container(
        workspace, project.resource_overrides
    )
    workspace.container_id = container_id
    workspace.url = url
    workspace.state = "running"

    await db.commit()
    return {"workspace_id": str(workspace.id), "url": url, "state": "running"}


@router.post("/pause")
async def pause_workspace(
    body: WorkspaceActionRequest,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    workspace = await _get_running_workspace(db, current_user.id, body.project_id)
    workspace_service.pause_container(workspace.container_id)
    workspace.state = "paused"
    await db.commit()
    return {"state": "paused"}


@router.post("/resume")
async def resume_workspace(
    body: WorkspaceActionRequest,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    workspace = await db.scalar(
        select(Workspace).where(
            Workspace.student_id == current_user.id,
            Workspace.project_id == body.project_id,
            Workspace.state == "paused",
        )
    )
    if not workspace:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No paused workspace found")
    workspace_service.resume_container(workspace.container_id)
    workspace.state = "running"
    await db.commit()
    return {"state": "running"}


@router.post("/reset")
async def reset_workspace(
    body: WorkspaceActionRequest,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """Stop container + remove volume, re-provision fresh."""
    workspace = await db.scalar(
        select(Workspace).where(
            Workspace.student_id == current_user.id,
            Workspace.project_id == body.project_id,
        )
    )
    if not workspace:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")

    if workspace.container_id:
        workspace_service.stop_and_remove_container(workspace.container_id)
    workspace_service.remove_volume(workspace.id)

    project = await db.get(Project, body.project_id)
    container_id, url = workspace_service.create_container(workspace, project.resource_overrides if project else None)
    workspace.container_id = container_id
    workspace.url = url
    workspace.state = "running"
    await db.commit()
    return {"state": "running", "url": url}


@router.post("/destroy")
async def destroy_workspace(
    body: WorkspaceActionRequest,
    current_user: TeacherUser,
    db: AsyncSession = Depends(get_db),
):
    """Teacher-only: destroy workspace and trigger archive task."""
    workspace = await db.scalar(
        select(Workspace).where(
            Workspace.project_id == body.project_id,
        )
    )
    if not workspace:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")

    if workspace.container_id:
        workspace_service.stop_and_remove_container(workspace.container_id)

    workspace.state = "destroyed"
    workspace.container_id = None
    await db.commit()

    # Trigger async archive
    from app.celery_app import archive_workspace_task
    archive_workspace_task.delay(str(workspace.id))

    return {"state": "destroyed"}


@router.post("/heartbeat")
async def heartbeat(
    body: WorkspaceActionRequest,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    """VS Code extension pings this to keep workspace alive."""
    from app.models.workspace import WorkspaceHeartbeat
    workspace = await db.scalar(
        select(Workspace).where(
            Workspace.student_id == current_user.id,
            Workspace.project_id == body.project_id,
        )
    )
    if not workspace:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")

    hb = await db.get(WorkspaceHeartbeat, workspace.id)
    if hb:
        hb.last_seen_at = datetime.now(timezone.utc)
    else:
        db.add(WorkspaceHeartbeat(workspace_id=workspace.id, last_seen_at=datetime.now(timezone.utc)))
    await db.commit()
    return {"ok": True}


async def _get_running_workspace(db: AsyncSession, student_id: uuid.UUID, project_id: uuid.UUID) -> Workspace:
    workspace = await db.scalar(
        select(Workspace).where(
            Workspace.student_id == student_id,
            Workspace.project_id == project_id,
            Workspace.state == "running",
        )
    )
    if not workspace:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No running workspace found")
    return workspace
