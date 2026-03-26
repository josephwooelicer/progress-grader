"""Consent check against the platform database."""
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


async def has_consent(db: AsyncSession, student_id: uuid.UUID, project_id: uuid.UUID) -> bool:
    """Return True if student has active (non-revoked) consent for project."""
    result = await db.execute(
        text(
            "SELECT 1 FROM consents "
            "WHERE student_id = :student_id "
            "  AND project_id = :project_id "
            "  AND revoked_at IS NULL "
            "LIMIT 1"
        ),
        {"student_id": student_id, "project_id": project_id},
    )
    return result.fetchone() is not None
