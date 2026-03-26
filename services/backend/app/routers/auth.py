"""Auth router: register, login, refresh, logout, verify (Traefik ForwardAuth)."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.models.user import RefreshToken, User
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_token,
    verify_password,
    verify_token_hash,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_OPTS = dict(httponly=True, samesite="lax", secure=True)


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str = "student"  # student | teacher | admin


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _set_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie("access_token", access_token, max_age=3600, **_COOKIE_OPTS)
    response.set_cookie("refresh_token", refresh_token, max_age=28800, **_COOKIE_OPTS)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        id=uuid.uuid4(),
        email=body.email,
        name=body.name,
        role=body.role,
        hashed_password=hash_password(body.password),
    )
    db.add(user)

    raw_refresh, expires_at = create_refresh_token()
    db.add(RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=expires_at,
    ))
    await db.commit()

    access = create_access_token(user.id, user.role)
    _set_cookies(response, access, raw_refresh)
    return {"id": str(user.id), "email": user.email, "role": user.role}


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(
        select(User).where(User.email == body.email, User.deleted_at.is_(None))
    )
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    raw_refresh, expires_at = create_refresh_token()
    db.add(RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=expires_at,
    ))
    await db.commit()

    access = create_access_token(user.id, user.role)
    _set_cookies(response, access, raw_refresh)
    return {"id": str(user.id), "email": user.email, "role": user.role}


@router.post("/refresh")
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")

    # Find unexpired, unrevoked tokens for any user and check hash
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    token_row = None
    for row in result.scalars().all():
        if verify_token_hash(refresh_token, row.token_hash):
            token_row = row
            break

    if not token_row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    # Revoke old token
    token_row.revoked_at = datetime.now(timezone.utc)

    user = await db.get(User, token_row.user_id)
    if not user or user.deleted_at:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    raw_refresh, expires_at = create_refresh_token()
    db.add(RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=expires_at,
    ))
    await db.commit()

    access = create_access_token(user.id, user.role)
    _set_cookies(response, access, raw_refresh)
    return {"ok": True}


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token:
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.revoked_at.is_(None))
        )
        for row in result.scalars().all():
            if verify_token_hash(refresh_token, row.token_hash):
                row.revoked_at = datetime.now(timezone.utc)
                break
        await db.commit()

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"ok": True}


@router.get("/verify")
async def verify(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Traefik ForwardAuth endpoint.
    Returns 200 with X-User-Id / X-User-Role headers, or 401.
    """
    token = request.cookies.get("access_token") or \
            (request.headers.get("Authorization", "").removeprefix("Bearer ").strip() or None)

    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No token")

    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    from fastapi.responses import Response as FastResponse
    resp = FastResponse()
    resp.headers["X-User-Id"] = payload["sub"]
    resp.headers["X-User-Role"] = payload["role"]
    return resp
