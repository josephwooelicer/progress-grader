"""Gitea webhook ingestion router."""
import hashlib
import hmac
import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from fastapi import Depends
from app.models.git_event import GitEvent

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_signature(body: bytes, signature: str | None, secret: str) -> bool:
    if not signature:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _parse_push(payload: dict) -> dict:
    commits = payload.get("commits", [])
    latest = commits[0] if commits else {}
    return {
        "event_type": "force_push" if payload.get("forced") else "push",
        "commit_sha": latest.get("id"),
        "commit_message": latest.get("message"),
        "branch_name": payload.get("ref", "").removeprefix("refs/heads/"),
        "forced": bool(payload.get("forced")),
    }


def _parse_create(payload: dict) -> dict:
    return {
        "event_type": "branch_create",
        "branch_name": payload.get("ref"),
        "forced": False,
        "commit_sha": None,
        "commit_message": None,
    }


def _parse_delete(payload: dict) -> dict:
    return {
        "event_type": "branch_delete",
        "branch_name": payload.get("ref"),
        "forced": False,
        "commit_sha": None,
        "commit_message": None,
    }


def _parse_pull_request(payload: dict) -> dict:
    pr = payload.get("pull_request", {})
    action = payload.get("action", "")
    if action == "opened":
        event_type = "pr_open"
    elif action in ("closed",) and pr.get("merged"):
        event_type = "pr_merge"
    else:
        return {}
    return {
        "event_type": event_type,
        "pr_number": pr.get("number"),
        "pr_title": pr.get("title"),
        "pr_description": pr.get("body"),
        "branch_name": pr.get("head", {}).get("label"),
        "forced": False,
        "commit_sha": pr.get("merge_commit_sha"),
        "commit_message": None,
    }


@router.post("/gitea", status_code=status.HTTP_204_NO_CONTENT)
async def gitea_webhook(
    request: Request,
    x_gitea_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()

    # Verify HMAC — use platform-wide webhook secret for now
    if not _verify_signature(body, x_gitea_signature, settings.gitea_webhook_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")

    payload: dict = await request.json()
    event_header = request.headers.get("X-Gitea-Event", "")

    # Extract student_id / project_id from repo name convention: {gitea_username}-{project_slug}
    # The repo's description field carries "student_id:project_id" for lookup
    repo = payload.get("repository", {})
    repo_description = repo.get("description", "")

    try:
        student_id_str, project_id_str = repo_description.split(":", 1)
        student_id = uuid.UUID(student_id_str)
        project_id = uuid.UUID(project_id_str)
    except (ValueError, AttributeError):
        # Cannot map to student/project — ignore gracefully
        return

    parsed: dict[str, Any] = {}
    if event_header == "push":
        parsed = _parse_push(payload)
    elif event_header == "create":
        parsed = _parse_create(payload)
    elif event_header == "delete":
        parsed = _parse_delete(payload)
    elif event_header == "pull_request":
        parsed = _parse_pull_request(payload)

    if not parsed:
        return

    event = GitEvent(
        id=uuid.uuid4(),
        student_id=student_id,
        project_id=project_id,
        payload=payload,
        **parsed,
    )
    db.add(event)
    await db.commit()
