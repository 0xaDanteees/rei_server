from typing import List, Optional, Set
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from ..security import get_current_user, AuthUser
from ..db import get_db
from ..models import (
    Partner,
    PartnerCreate,
    PartnerUpdate,
    PartnerResponse,
    PartnerSearchFilters,
)

router = APIRouter()


def _parse_includes(include: Optional[str]) -> Set[str]:
    if not include:
        return set()
    return {part.strip().lower() for part in include.split(",") if part.strip()}


async def _get_owned_partner(session: AsyncSession, user_id: UUID, partner_id: UUID, includes: Set[str]) -> Partner:
    stmt = select(Partner).where(Partner.id == partner_id, Partner.user_id == user_id)
    if "clothing" in includes:
        stmt = stmt.options(selectinload(Partner.clothing_items).selectinload("clothing_item"))
    if "piercings" in includes:
        stmt = stmt.options(selectinload(Partner.piercings))
    if "tattoos" in includes:
        stmt = stmt.options(selectinload(Partner.tattoos))
    result = await session.execute(stmt)
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    return partner


 


@router.get("", response_model=List[PartnerResponse])
async def list_partners(
    include: Optional[str] = Query(None, description="comma-separated: clothing,piercings,tattoos"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    includes = _parse_includes(include)
    stmt = (
        select(Partner)
        .where(Partner.user_id == user.user_id)
        .order_by(Partner.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if "clothing" in includes:
        stmt = stmt.options(selectinload(Partner.clothing_items).selectinload("clothing_item"))
    if "piercings" in includes:
        stmt = stmt.options(selectinload(Partner.piercings))
    if "tattoos" in includes:
        stmt = stmt.options(selectinload(Partner.tattoos))

    result = await session.execute(stmt)
    partners = result.scalars().all()
    return partners


@router.post("", response_model=PartnerResponse, status_code=status.HTTP_201_CREATED)
async def create_partner(
    body: PartnerCreate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        obj = Partner(**body.model_dump(exclude={"user_id"}))
        obj.user_id = user.user_id
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj
    except Exception:
        await session.rollback()
        raise


@router.get("/{partner_id}", response_model=PartnerResponse)
async def get_partner(
    partner_id: UUID,
    include: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    includes = _parse_includes(include)
    obj = await _get_owned_partner(session, user.user_id, partner_id, includes)
    return obj


@router.patch("/{partner_id}", response_model=PartnerResponse)
async def update_partner(
    partner_id: UUID,
    body: PartnerUpdate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    includes: Set[str] = set()
    obj = await _get_owned_partner(session, user.user_id, partner_id, includes)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)
    try:
        await session.commit()
        await session.refresh(obj)
        return obj
    except Exception:
        await session.rollback()
        raise


@router.delete("/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_partner(
    partner_id: UUID,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    obj = await _get_owned_partner(session, user.user_id, partner_id, set())
    try:
        await session.delete(obj)
        await session.commit()
    except Exception:
        await session.rollback()
        raise


@router.get("/search", response_model=List[PartnerResponse])
async def search_partners(
    filters: PartnerSearchFilters = Depends(),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    includes = _parse_includes(include)
    stmt = select(Partner).where(Partner.user_id == user.user_id)
    if filters.gender:
        stmt = stmt.where(Partner.gender == filters.gender)
    if filters.body_type:
        stmt = stmt.where(Partner.body_type == filters.body_type)
    if filters.skin_tone:
        stmt = stmt.where(Partner.skin_tone == filters.skin_tone)
    if filters.hair_style:
        stmt = stmt.where(Partner.hair_style == filters.hair_style)
    if filters.fitness_level:
        stmt = stmt.where(Partner.fitness_level == filters.fitness_level)
    if filters.age_min is not None:
        stmt = stmt.where(Partner.age >= filters.age_min)
    if filters.age_max is not None:
        stmt = stmt.where(Partner.age <= filters.age_max)
    stmt = stmt.order_by(Partner.created_at.desc()).limit(limit).offset(offset)

    if "clothing" in includes:
        stmt = stmt.options(selectinload(Partner.clothing_items).selectinload("clothing_item"))
    if "piercings" in includes:
        stmt = stmt.options(selectinload(Partner.piercings))
    if "tattoos" in includes:
        stmt = stmt.options(selectinload(Partner.tattoos))

    result = await session.execute(stmt)
    return result.scalars().all()

# partner router