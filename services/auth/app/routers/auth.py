from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..dependencies import get_db, get_current_user
from ..models import User, RevokedToken, PasswordResetToken
from ..schemas import RegisterIn, LoginIn, ForgotPasswordIn, ResetPasswordIn, TokenOut, UserOut, ChangePasswordIn
from ..security import hash_password, verify_password, create_access_token, decode_token, validate_password_strength

router = APIRouter()
bearer = HTTPBearer(auto_error=False)
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", status_code=201)
@limiter.limit("5/minute")  # Strict limit for registration
async def register(request: Request, payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    try:
        res = await db.execute(select(User).where(User.email.ilike(payload.email), User.is_nuked == False).limit(1))  # noqa: E712
        if res.scalars().first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
        # password policy validation
        ok, msg = validate_password_strength(payload.password)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
        user = User(email=payload.email.lower(), password_hash=hash_password(payload.password))
        db.add(user)
        await db.commit()
        await db.refresh(user)
        payload_out = UserOut.model_validate(user).model_dump()
        return {"status": status.HTTP_201_CREATED, "message": "User created", "payload": payload_out}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")


@router.post("/login")
@limiter.limit("10/minute")  # Prevent brute force attacks
async def login(request: Request, payload: LoginIn, db: AsyncSession = Depends(get_db)):
    try:
        res = await db.execute(select(User).where(User.email.ilike(payload.email), User.is_nuked == False).limit(1))  # noqa: E712
        user = res.scalars().first()
        if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials")
        token, jti, exp = create_access_token(sub=user.email)
        return {"status": status.HTTP_200_OK, "message": "Logged in", "payload": {"access_token": token, "token_type": "bearer", "expires_in": exp}}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to log in")


@router.post("/logout")
@limiter.limit("20/minute")
async def logout(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: AsyncSession = Depends(get_db),
):
    if not creds:
        return {"status": status.HTTP_200_OK, "message": "No token provided", "payload": {}}
    try:
        payload = decode_token(creds.credentials)
    except Exception:
        return {"status": status.HTTP_200_OK, "message": "Token invalid or expired", "payload": {}}
    jti = payload.get("jti")
    sub = payload.get("sub")
    exp = payload.get("exp")
    if not (jti and sub and exp):
        return {"status": status.HTTP_200_OK, "message": "Token missing fields", "payload": {}}
    res = await db.execute(select(User).where(User.email.ilike(sub)).limit(1))
    user = res.scalars().first()
    if not user:
        return {"status": status.HTTP_200_OK, "message": "User not found", "payload": {}}
    db.add(RevokedToken(jti=jti, user_id=user.id, expires_at=datetime.fromtimestamp(exp, tz=timezone.utc)))
    await db.commit()
    return {"status": status.HTTP_200_OK, "message": "Logged out", "payload": {}}


@router.post("/forgot-password", status_code=202)
async def forgot_password(payload: ForgotPasswordIn, db: AsyncSession = Depends(get_db)):
    try:
        res = await db.execute(select(User).where(User.email.ilike(payload.email), User.is_nuked == False).limit(1))  # noqa: E712
        user = res.scalars().first()
        if not user:
            return {"status": status.HTTP_202_ACCEPTED, "message": "If the account exists, an email will be sent", "payload": {}}
        token = secrets.token_urlsafe(32)
        pr = PasswordResetToken(
            token=token,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(pr)
        await db.commit()
        # TODO: send email in production
        return {"status": status.HTTP_202_ACCEPTED, "message": "Password reset initiated", "payload": {"reset_token_dev_only": token}}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initiate password reset")


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordIn, db: AsyncSession = Depends(get_db)):
    try:
        res = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token == payload.token,
                PasswordResetToken.consumed == False,  # noqa: E712
                PasswordResetToken.expires_at > datetime.now(timezone.utc),
            ).limit(1)
        )
        pr = res.scalars().first()
        if not pr:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
        # consume and update password
        from sqlalchemy import update
        await db.execute(update(PasswordResetToken).where(PasswordResetToken.token == payload.token).values(consumed=True))
        await db.execute(update(User).where(User.id == pr.user_id).values(password_hash=hash_password(payload.new_password)))
        await db.commit()
        return {"status": status.HTTP_200_OK, "message": "Password reset successful", "payload": {}}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reset password")


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordIn,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        # Verify current password for the authenticated user
        if not verify_password(payload.current_password, current.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials")

        # Validate new password strength (do not impact existing users until they change)
        ok, msg = validate_password_strength(payload.new_password)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

        # Update password hash
        from sqlalchemy import update
        await db.execute(
            update(User)
            .where(User.id == current.id)
            .values(password_hash=hash_password(payload.new_password))
        )
        await db.commit()
        return {"status": status.HTTP_200_OK, "message": "Password changed successfully", "payload": {}}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to change password")