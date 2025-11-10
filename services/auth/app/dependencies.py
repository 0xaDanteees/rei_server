from __future__ import annotations

from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db as _get_db
from .models import User, RevokedToken
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


# Expose DB dependency to routers
async def get_db() -> AsyncSession:
    async for session in _get_db():
        yield session


# Common auth dependency for protected routes
async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    jti = payload.get("jti")
    sub = payload.get("sub")
    if not (jti and sub):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Check revocation
    revoked = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti).limit(1))
    if revoked.scalars().first():
        raise HTTPException(status_code=401, detail="Token revoked")

    # Resolve user by UUID from token subject
    try:
        user_id = UUID(sub)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    res = await db.execute(select(User).where(User.id == user_id).limit(1))
    user = res.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive or missing user")
    return user


# Variant that allows inactive users (for reactivation and account nuke flows)
async def get_current_user_allow_inactive(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    jti = payload.get("jti")
    sub = payload.get("sub")
    if not (jti and sub):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    revoked = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti).limit(1))
    if revoked.scalars().first():
        raise HTTPException(status_code=401, detail="Token revoked")

    try:
        user_id = UUID(sub)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    res = await db.execute(select(User).where(User.id == user_id).limit(1))
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="Inactive or missing user")
    # Allow inactive here, but block nuked accounts
    try:
        if getattr(user, "is_nuked", False):
            raise HTTPException(status_code=403, detail="User is nuked")
    except Exception:
        # If model doesn't have is_nuked yet (before migration), treat as not nuked
        pass
    return user
