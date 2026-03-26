from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Cookie, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.consent import Consent
from app.models.user import User


def _decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


async def get_current_user(
    access_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    if not access_token:
        raise HTTPException(401, "Not authenticated")
    payload = _decode_jwt(access_token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid token payload")
    result = await db.execute(
        select(User).where(User.id == UUID(user_id), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(401, "User not found")
    return user


def require_role(*roles: str):
    async def check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return check


async def require_consent(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Consent).where(
            Consent.student_id == user.id,
            Consent.project_id == project_id,
            Consent.revoked_at.is_(None),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(403, "Student has not consented for this project")


# Shorthand typed dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]
StudentUser = Annotated[User, Depends(require_role("student", "admin"))]
TeacherUser = Annotated[User, Depends(require_role("teacher", "admin"))]
AdminUser = Annotated[User, Depends(require_role("admin"))]
DB = Annotated[AsyncSession, Depends(get_db)]
