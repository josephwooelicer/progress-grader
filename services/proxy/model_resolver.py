"""
Resolve the AI provider and model for a given student + project.

Priority: student override → project config → platform env default.
"""
import os
import uuid

from cryptography.fernet import Fernet
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")


def _decrypt(value: str) -> str:
    return Fernet(_ENCRYPTION_KEY.encode()).decrypt(value.encode()).decode()


async def resolve_model(
    db: AsyncSession,
    student_id: uuid.UUID,
    project_id: uuid.UUID | None,
) -> tuple[str, str, str]:
    """
    Return (provider, model, api_key).
    Falls back through student → project → platform env.
    """
    # 1. Student-level override
    if project_id:
        row = await db.execute(
            text(
                "SELECT provider, model, api_key_encrypted "
                "FROM student_project_settings "
                "WHERE student_id = :sid AND project_id = :pid "
                "LIMIT 1"
            ),
            {"sid": student_id, "pid": project_id},
        )
        student_settings = row.fetchone()
        if student_settings and student_settings.api_key_encrypted:
            return (
                student_settings.provider or os.environ.get("DEFAULT_PROVIDER", "openai"),
                student_settings.model or os.environ.get("DEFAULT_MODEL", "gpt-4o"),
                _decrypt(student_settings.api_key_encrypted),
            )

    # 2. Project-level config
    if project_id:
        row = await db.execute(
            text(
                "SELECT provider, model, api_key_encrypted "
                "FROM projects WHERE id = :pid LIMIT 1"
            ),
            {"pid": project_id},
        )
        project = row.fetchone()
        if project and project.api_key_encrypted:
            return (
                project.provider or os.environ.get("DEFAULT_PROVIDER", "openai"),
                project.model or os.environ.get("DEFAULT_MODEL", "gpt-4o"),
                _decrypt(project.api_key_encrypted),
            )

    # 3. Platform env default
    return (
        os.environ.get("DEFAULT_PROVIDER", "openai"),
        os.environ.get("DEFAULT_MODEL", "gpt-4o"),
        os.environ.get("DEFAULT_API_KEY", ""),
    )
