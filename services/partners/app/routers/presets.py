# presets router

from typing import Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..security import get_current_user, AuthUser
from ..db import get_db
from ..models import (
    PARTNER_PRESETS,
    Partner,
    PartnerBase,
    PartnerResponse,
    PartnerClothing,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

router = APIRouter()


@router.get("", response_model=List[Dict[str, Any]])
async def list_presets(_: AuthUser = Depends(get_current_user)):
    out = []
    for key, preset in PARTNER_PRESETS.items():
        out.append({
            "key": key,
            "name": preset.name,
            "description": preset.description,
        })
    return out


@router.post("/apply/{preset_key}", response_model=PartnerResponse, status_code=status.HTTP_201_CREATED)
async def apply_preset(
    preset_key: str,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        preset = PARTNER_PRESETS.get(preset_key)
        if not preset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")
        data: PartnerBase = preset.partner_data
        obj = Partner(**data.model_dump())
        obj.user_id = user.user_id
        session.add(obj)
        await session.commit()
        # Eagerly load relationships before returning
        stmt = (
            select(Partner)
            .where(Partner.id == obj.id, Partner.user_id == user.user_id)
            .options(
                selectinload(Partner.clothing_items).selectinload(PartnerClothing.clothing_item),
                selectinload(Partner.piercings),
                selectinload(Partner.tattoos),
            )
        )
        result = await session.execute(stmt)
        obj_loaded = result.scalar_one()
        return obj_loaded
    except Exception:
        await session.rollback()
        raise
