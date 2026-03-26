"""JWT verification for the AI proxy."""
import os

import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "")
ALGORITHM = "HS256"


def verify_jwt(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
