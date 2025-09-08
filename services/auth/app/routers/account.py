from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db, get_current_user_allow_inactive
from ..models import User
from ..schemas import AccountActionIn
from ..security import verify_password

router = APIRouter()


@router.post("/deactivate")
async def deactivate(
    payload: AccountActionIn,
    current: User = Depends(get_current_user_allow_inactive),
    db: AsyncSession = Depends(get_db),
):
    # Verify password
    if not verify_password(payload.password, current.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid password")

    try:
        await db.execute(update(User).where(User.id == current.id).values(is_active=False))
        await db.commit()
        return {"status": status.HTTP_200_OK, "message": "User deactivated", "payload": {}}
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to deactivate user")


@router.post("/reactivate")
async def reactivate(
    payload: AccountActionIn,
    current: User = Depends(get_current_user_allow_inactive),
    db: AsyncSession = Depends(get_db),
):
    # Verify password even if user is inactive
    if not verify_password(payload.password, current.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid password")

    try:
        # Block nuked users from reactivating
        if getattr(current, "is_nuked", False):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is nuked")

        await db.execute(update(User).where(User.id == current.id).values(is_active=True))
        await db.commit()
        return {"status": status.HTTP_200_OK, "message": "User reactivated", "payload": {}}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reactivate user")


@router.delete("/nuke")
async def nuke(
    payload: AccountActionIn,
    current: User = Depends(get_current_user_allow_inactive),
    db: AsyncSession = Depends(get_db),
):
    # Verify password
    if not verify_password(payload.password, current.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid password")

    try:
        # Soft delete: mark as nuked and deactivate account
        await db.execute(
            update(User)
            .where(User.id == current.id)
            .values(is_nuked=True, is_active=False)
        )
        await db.commit()
        return {"status": status.HTTP_200_OK, "message": "User nuked", "payload": {}}
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to nuke user")
