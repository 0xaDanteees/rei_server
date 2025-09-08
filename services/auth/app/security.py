from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import jwt
from passlib.context import CryptContext
from .settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(sub: str, expires_in: int | None = None) -> tuple[str, str, int]:
    now = datetime.now(timezone.utc)
    exp_seconds = expires_in or settings.ACCESS_TOKEN_EXPIRE_SECONDS
    exp = now + timedelta(seconds=exp_seconds)
    jti = uuid.uuid4().hex
    payload: Dict[str, Any] = {
        "iss": settings.JWT_ISSUER,
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": jti,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return token, jti, exp_seconds


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password policy: >=8 chars, at least one uppercase, one lowercase,
    one digit, and one special character. Returns (ok, message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if password.lower() == password:
        return False, "Password must include at least one uppercase letter"
    if password.upper() == password:
        return False, "Password must include at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must include at least one number"
    specials = set("!@#$%^&*()-_=+[{]}\\|;:'\",<.>/?`~")
    if not any(c in specials for c in password):
        return False, "Password must include at least one special character"
    return True, "OK"
