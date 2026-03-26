"""Consent router: POST /api/consent"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import StudentUser
from app.models.consent import Consent

router = APIRouter(prefix="/api/consent", tags=["consent"])

AGREEMENT_TEXT = (
    "I consent to the collection and storage of my AI conversation history "
    "and Git activity for this project. This data will be visible to my teacher "
    "for grading purposes. I understand this consent is for this project only and "
    "cannot be revoked once given."
)


class ConsentRequest(BaseModel):
    project_id: uuid.UUID


@router.post("", status_code=status.HTTP_201_CREATED)
async def give_consent(
    body: ConsentRequest,
    request: Request,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(
        select(Consent).where(
            Consent.student_id == current_user.id,
            Consent.project_id == body.project_id,
        )
    )
    if existing:
        return {"ok": True, "already_consented": True}

    ip = request.client.host if request.client else None
    consent = Consent(
        id=uuid.uuid4(),
        student_id=current_user.id,
        project_id=body.project_id,
        agreed_at=datetime.now(timezone.utc),
        agreement_text=AGREEMENT_TEXT,
        ip_address=ip,
    )
    db.add(consent)
    await db.commit()
    return {"ok": True, "already_consented": False}


@router.get("/text")
async def get_consent_text():
    """Return the consent agreement text for the frontend to display."""
    return {"text": AGREEMENT_TEXT}
