import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_HOURS = 8


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def hash_token(token: str) -> str:
    """Hash a refresh token for storage (bcrypt)."""
    return _pwd_context.hash(token)


def verify_token_hash(token: str, hashed: str) -> bool:
    return _pwd_context.verify(token, hashed)


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_refresh_token() -> tuple[str, datetime]:
    """Return (raw_token, expires_at). Store hash, send raw."""
    raw = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS)
    return raw, expires_at


def decode_access_token(token: str) -> dict:
    """Decode and validate access token. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
