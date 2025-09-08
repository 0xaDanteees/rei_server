from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, Avatar, RevokedToken, PasswordResetToken
from .security import hash_password, verify_password

# Users
async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    stmt = select(User).where(func.lower(User.email) == func.lower(email)).limit(1)
    res = await db.execute(stmt)
    return res.scalars().first()

async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    res = await db.execute(select(User).where(User.id == user_id).limit(1))
    return res.scalars().first()

async def create_user(db: AsyncSession, email: str, password: str) -> User:
    user = User(email=email.lower(), password_hash=hash_password(password))
    db.add(user)
    await db.flush()
    return user

async def verify_user_credentials(db: AsyncSession, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if user and user.is_active and verify_password(password, user.password_hash):
        return user
    return None

async def deactivate_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(update(User).where(User.id == user_id).values(is_active=False))

# Tokens (logout via blacklist)
async def revoke_token(db: AsyncSession, jti: str, user_id: uuid.UUID, exp_ts: int) -> None:
    expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
    db.add(RevokedToken(jti=jti, user_id=user_id, expires_at=expires_at))

async def is_token_revoked(db: AsyncSession, jti: str) -> bool:
    res = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti).limit(1))
    return res.scalars().first() is not None

# Password reset
async def create_password_reset(db: AsyncSession, user_id: uuid.UUID, token: str, expires_in_seconds: int = 3600) -> PasswordResetToken:
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
    pr = PasswordResetToken(token=token, user_id=user_id, expires_at=expires_at)
    db.add(pr)
    await db.flush()
    return pr

async def consume_password_reset(db: AsyncSession, token: str, new_password: str) -> Optional[uuid.UUID]:
    res = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == token,
            PasswordResetToken.consumed == False,  # noqa: E712
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        ).limit(1)
    )
    pr = res.scalars().first()
    if not pr:
        return None
    await db.execute(update(PasswordResetToken).where(PasswordResetToken.token == token).values(consumed=True))
    await db.execute(update(User).where(User.id == pr.user_id).values(password_hash=hash_password(new_password)))
    return pr.user_id

# Avatars
async def upsert_avatar(db: AsyncSession, user_id: uuid.UUID, path: str, mime: str) -> None:
    res = await db.execute(select(Avatar).where(Avatar.user_id == user_id).limit(1))
    avatar = res.scalars().first()
    if avatar:
        await db.execute(update(Avatar).where(Avatar.user_id == user_id).values(path=path, mime_type=mime))
    else:
        db.add(Avatar(user_id=user_id, path=path, mime_type=mime))
