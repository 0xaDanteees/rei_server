from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List

import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db, get_current_user, get_current_user_allow_inactive
from ..models import User, Avatar
from ..schemas import MeOut, AvatarUploadOut
from ..settings import settings

router = APIRouter()
logger = logging.getLogger("auth.user")


@router.get("/me")
async def me(
    request: Request,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    include: List[str] = Query(default=[]),
):
    try:
        # Base payload
        payload = MeOut.model_validate(current).model_dump()
        # Optionally include avatar URL if requested
        if "avatar" in {i.lower() for i in include}:
            res = await db.execute(select(Avatar).where(Avatar.user_id == current.id).limit(1))
            avatar = res.scalars().first()
            if avatar:
                if request is not None:
                    try:
                        # absolute URL to the avatar endpoint
                        payload["avatar_url"] = str(request.url_for("get_avatar"))
                    except Exception:
                        payload["avatar_url"] = "/user/avatar"
                else:
                    payload["avatar_url"] = "/user/avatar"
        return {"status": status.HTTP_200_OK, "message": "OK", "payload": payload}
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get user")


## moved to account router


@router.post("/avatar", status_code=201)
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    mime = file.content_type or ""
    if mime not in ("image/png", "image/jpeg"):
        raise HTTPException(status_code=415, detail="Only PNG or JPG allowed")

    # Resolve avatar directory to absolute path and ensure it exists
    try:
        avatar_dir = Path(settings.AVATAR_DIR).expanduser().resolve()
        avatar_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.exception("Failed to prepare avatar directory: %s", settings.AVATAR_DIR)
        raise HTTPException(status_code=500, detail="Avatar storage not available") from e

    # If an avatar exists, remove it (file + row) before saving the new one
    res = await db.execute(select(Avatar).where(Avatar.user_id == current.id).limit(1))
    existing = res.scalars().first()
    if existing:
        try:
            Path(existing.path).unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            logger.warning("Failed to remove previous avatar file at %s", existing.path)
        await db.execute(delete(Avatar).where(Avatar.user_id == current.id))

    ext = ".png" if mime == "image/png" else ".jpg"
    filename = f"{current.id}{ext}"
    path = avatar_dir / filename

    # enforce size limit
    try:
        size = 0
        with open(path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.MAX_AVATAR_MB * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="Avatar too large")
                f.write(chunk)
    except HTTPException:
        # re-raise known HTTP errors
        raise
    except Exception as e:
        logger.exception("Failed to write avatar file to %s", str(path))
        raise HTTPException(status_code=500, detail="Failed to store avatar") from e

    # insert avatar row
    db.add(Avatar(user_id=current.id, path=str(path), mime_type=mime))
    await db.commit()

    # Build absolute URL if Request available
    url = "/user/avatar"
    if request is not None:
        try:
            url = str(request.url_for("get_avatar"))
        except Exception:
            pass
    return {"status": status.HTTP_201_CREATED, "message": "Avatar uploaded", "payload": {"url": url}}


@router.get("/avatar")
async def get_avatar(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        res = await db.execute(select(Avatar).where(Avatar.user_id == current.id).limit(1))
        a = res.scalars().first()
        if not a:
            raise HTTPException(status_code=404)
        return FileResponse(a.path, media_type=a.mime_type)
    except HTTPException:
        # Preserve intended HTTP status (e.g., 404 when no avatar)
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get avatar")


@router.delete("/avatar")
async def delete_avatar(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        res = await db.execute(select(Avatar).where(Avatar.user_id == current.id).limit(1))
        a = res.scalars().first()
        if not a:
            return {"status": status.HTTP_200_OK, "message": "No avatar to delete", "payload": {}}
        # delete file best-effort
        try:
            Path(a.path).unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            logger.warning("Failed to remove avatar file at %s", a.path)
        # delete row
        await db.execute(delete(Avatar).where(Avatar.user_id == current.id))
        await db.commit()
        return {"status": status.HTTP_200_OK, "message": "Avatar deleted", "payload": {}}
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete avatar")