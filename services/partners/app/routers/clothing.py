# clothing router

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..security import get_current_user, AuthUser
from ..db import get_db
from ..models import (
    ClothingItem,
    ClothingItemResponse,
    ClothingItemCreate,
    ClothingItemUpdate,
    Partner,
    PartnerClothing,
    PartnerClothingCreate,
    PartnerClothingUpdate,
    PartnerClothingResponse,
)

router = APIRouter()


async def _ensure_owned_partner(session: AsyncSession, user_id: UUID, partner_id: UUID) -> Partner:
    stmt = select(Partner).where(Partner.id == partner_id, Partner.user_id == user_id)
    res = await session.execute(stmt)
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    return obj


@router.get("/catalog", response_model=List[ClothingItemResponse])
async def list_catalog(
    category: Optional[str] = Query(None),
    sub_category: Optional[str] = Query(None),
    is_premium: Optional[bool] = Query(None),
    is_gift: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(ClothingItem).order_by(ClothingItem.created_at.desc()).limit(limit).offset(offset)
    if category:
        stmt = stmt.where(ClothingItem.category == category)
    if sub_category:
        stmt = stmt.where(ClothingItem.sub_category == sub_category)
    if is_premium is not None:
        stmt = stmt.where(ClothingItem.is_premium == is_premium)
    if is_gift is not None:
        stmt = stmt.where(ClothingItem.is_gift == is_gift)
    res = await session.execute(stmt)
    return res.scalars().all()


@router.get("/partner/{partner_id}", response_model=List[PartnerClothingResponse])
async def list_partner_clothing(
    partner_id: UUID,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await _ensure_owned_partner(session, user.user_id, partner_id)
    stmt = (
        select(PartnerClothing)
        .where(PartnerClothing.partner_id == partner_id)
        .options(selectinload(PartnerClothing.clothing_item))
        .order_by(PartnerClothing.id)
    )
    res = await session.execute(stmt)
    return res.scalars().all()


@router.post("/partner/{partner_id}", response_model=PartnerClothingResponse, status_code=status.HTTP_201_CREATED)
async def add_partner_clothing(
    partner_id: UUID,
    body: PartnerClothingCreate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await _ensure_owned_partner(session, user.user_id, partner_id)
    # Validate clothing exists
    cstmt = select(ClothingItem).where(ClothingItem.id == body.clothing_item_id)
    cres = await session.execute(cstmt)
    if not cres.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clothing item not found")
    obj = PartnerClothing(
        partner_id=partner_id,
        clothing_item_id=body.clothing_item_id,
        is_equipped=body.is_equipped,
        slot=body.slot,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.patch("/{partner_clothing_id}", response_model=PartnerClothingResponse)
async def update_partner_clothing(
    partner_clothing_id: UUID,
    body: PartnerClothingUpdate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = (
        select(PartnerClothing)
        .where(PartnerClothing.id == partner_clothing_id)
        .options(selectinload(PartnerClothing.clothing_item))
    )
    res = await session.execute(stmt)
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner clothing not found")
    # Ownership via partner
    await _ensure_owned_partner(session, user.user_id, obj.partner_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.delete("/{partner_clothing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_partner_clothing(
    partner_clothing_id: UUID,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(PartnerClothing).where(PartnerClothing.id == partner_clothing_id)
    res = await session.execute(stmt)
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner clothing not found")
    await _ensure_owned_partner(session, user.user_id, obj.partner_id)
    await session.delete(obj)
    await session.commit()

# clothing router