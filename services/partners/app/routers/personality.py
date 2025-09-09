# personality router

from typing import List, Optional, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from ..security import get_current_user, AuthUser
from ..db import get_db
from ..models import (
    Partner,
    PersonalityTraits,
    PersonalityRarity,
    PersonalityCoreItem,
    PERSONALITY_TRAIT_RARITY,
) 

router = APIRouter()


async def _ensure_owned_partner(session: AsyncSession, user_id: UUID, partner_id: UUID) -> Partner:
    try:
        stmt = select(Partner).where(Partner.id == partner_id, Partner.user_id == user_id)
        res = await session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
        return obj
    except Exception:
        await session.rollback()
        raise

@router.get("/{partner_id}", response_model=List[PersonalityCoreItem])
async def get_partner_personality(partner_id: UUID, user: AuthUser = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    try:
        await _ensure_owned_partner(session, user.user_id, partner_id)
        stmt = select(Partner).where(Partner.id == partner_id)
        res = await session.execute(stmt)
        partner = res.scalar_one_or_none()
        if not partner:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
        return partner.personality_core or []
    except Exception:
        await session.rollback()
        raise


class PersonalityPatch(BaseModel):
    action: Literal["add", "replace", "remove"]
    trait: Optional[PersonalityTraits] = None
    rarity: Optional[PersonalityRarity] = None
    # For replace/remove operations, specify the target trait to look for
    target_trait: Optional[PersonalityTraits] = None


@router.patch("/{partner_id}", response_model=List[PersonalityCoreItem])
async def update_partner_personality(
    partner_id: UUID,
    body: PersonalityPatch,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        await _ensure_owned_partner(session, user.user_id, partner_id)
        stmt = select(Partner).where(Partner.id == partner_id)
        res = await session.execute(stmt)
        partner = res.scalar_one_or_none()
        if not partner:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")

        current: List[dict] = list(partner.personality_core or [])

        def _exists(tr: PersonalityTraits) -> bool:
            return any(item.get("trait") == tr.value for item in current)

        if body.action == "add":
            if not body.trait:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="trait is required for add")
            if _exists(body.trait):
                # Idempotent add
                return current
            rarity = body.rarity or PERSONALITY_TRAIT_RARITY.get(body.trait)
            if not rarity:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rarity not found for trait")
            current.append({"trait": body.trait.value, "rarity": rarity.value})

        elif body.action == "replace":
            if not body.target_trait or not body.trait:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_trait and trait are required for replace")
            # If replacing with the same, no-op
            if body.target_trait == body.trait:
                return current
            # enforce uniqueness: remove any existing new trait first
            current = [it for it in current if it.get("trait") != body.trait.value]
            found = False
            for it in current:
                if it.get("trait") == body.target_trait.value:
                    rarity = body.rarity or PERSONALITY_TRAIT_RARITY.get(body.trait)
                    if not rarity:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rarity not found for trait")
                    it["trait"] = body.trait.value
                    it["rarity"] = rarity.value
                    found = True
                    break
            if not found:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="target_trait not found in personality_core")

        elif body.action == "remove":
            if not body.target_trait:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_trait is required for remove")
            before = len(current)
            current = [it for it in current if it.get("trait") != body.target_trait.value]
            if len(current) == before:
                # If not found, respond 404 to be explicit
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="target_trait not found in personality_core")

        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid action")

        partner.personality_core = current
        await session.commit()
        await session.refresh(partner)
        return partner.personality_core or []
    except HTTPException:
        # pass through known errors without extra rollback handler message
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise
