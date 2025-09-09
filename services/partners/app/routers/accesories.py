# accesories router

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..security import get_current_user, AuthUser
from ..db import get_db
from ..models import (
    Partner,
    PartnerPiercing,
    PartnerPiercingBase,
    PartnerPiercingCreate,
    PartnerPiercingUpdate,
    PartnerPiercingResponse,
    PartnerTattoo,
    PartnerTattooBase,
    PartnerTattooCreate,
    PartnerTattooUpdate,
    PartnerTattooResponse,
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


# Piercings
@router.get("/piercings/{partner_id}", response_model=List[PartnerPiercingResponse])
async def list_piercings(partner_id: UUID, user: AuthUser = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    try:
        await _ensure_owned_partner(session, user.user_id, partner_id)
        stmt = select(PartnerPiercing).where(PartnerPiercing.partner_id == partner_id)
        res = await session.execute(stmt)
        return res.scalars().all()
    except Exception:
        await session.rollback()
        raise


@router.post("/piercings/{partner_id}", response_model=PartnerPiercingResponse, status_code=status.HTTP_201_CREATED)
async def add_piercing(partner_id: UUID, body: PartnerPiercingCreate, user: AuthUser = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    try:
        await _ensure_owned_partner(session, user.user_id, partner_id)
        obj = PartnerPiercing(
            partner_id=partner_id,
            location=body.location,
            jewelry_type=body.jewelry_type,
            jewelry_material=body.jewelry_material,
            jewelry_color=body.jewelry_color,
            size=body.size,
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj
    except Exception:
        await session.rollback()
        raise


@router.patch("/piercings/{piercing_id}", response_model=PartnerPiercingResponse)
async def update_piercing(piercing_id: UUID, body: PartnerPiercingUpdate, user: AuthUser = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    try:
        stmt = select(PartnerPiercing).where(PartnerPiercing.id == piercing_id)
        res = await session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Piercing not found")
        await _ensure_owned_partner(session, user.user_id, obj.partner_id)
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        await session.commit()
        await session.refresh(obj)
        return obj
    except Exception:
        await session.rollback()
        raise


@router.delete("/piercings/{piercing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_piercing(piercing_id: UUID, user: AuthUser = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    try:
        stmt = select(PartnerPiercing).where(PartnerPiercing.id == piercing_id)
        res = await session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Piercing not found")
        await _ensure_owned_partner(session, user.user_id, obj.partner_id)
        await session.delete(obj)
        await session.commit()
    except Exception:
        await session.rollback()
        raise


# Tattoos
@router.get("/tattoos/{partner_id}", response_model=List[PartnerTattooResponse])
async def list_tattoos(partner_id: UUID, user: AuthUser = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    try:
        await _ensure_owned_partner(session, user.user_id, partner_id)
        stmt = select(PartnerTattoo).where(PartnerTattoo.partner_id == partner_id)
        res = await session.execute(stmt)
        return res.scalars().all()
    except Exception:
        await session.rollback()
        raise


@router.post("/tattoos/{partner_id}", response_model=PartnerTattooResponse, status_code=status.HTTP_201_CREATED)
async def add_tattoo(partner_id: UUID, body: PartnerTattooCreate, user: AuthUser = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    try:
        await _ensure_owned_partner(session, user.user_id, partner_id)
        obj = PartnerTattoo(
            partner_id=partner_id,
            location=body.location,
            tattoo_type=body.tattoo_type,
            tattoo_style=body.tattoo_style,
            tattoo_color=body.tattoo_color,
            size=body.size,
            image_url=body.image_url,
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj
    except Exception:
        await session.rollback()
        raise


@router.patch("/tattoos/{tattoo_id}", response_model=PartnerTattooResponse)
async def update_tattoo(tattoo_id: UUID, body: PartnerTattooUpdate, user: AuthUser = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    try:
        stmt = select(PartnerTattoo).where(PartnerTattoo.id == tattoo_id)
        res = await session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tattoo not found")
        await _ensure_owned_partner(session, user.user_id, obj.partner_id)
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        await session.commit()
        await session.refresh(obj)
        return obj
    except Exception:
        await session.rollback()
        raise


@router.delete("/tattoos/{tattoo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tattoo(tattoo_id: UUID, user: AuthUser = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    try:
        stmt = select(PartnerTattoo).where(PartnerTattoo.id == tattoo_id)
        res = await session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tattoo not found")
        await _ensure_owned_partner(session, user.user_id, obj.partner_id)
        await session.delete(obj)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
