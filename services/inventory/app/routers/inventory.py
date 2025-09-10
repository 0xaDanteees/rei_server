# inventory router - user inventory management

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from ..security import get_current_user, AuthUser
from ..db import get_db
from ..models import (
    UserInventory,
    Product,
    UserInventoryCreate,
    UserInventoryUpdate,
    UserInventoryResponse,
    AcquisitionMethod,
)

router = APIRouter()


@router.get("/", response_model=List[UserInventoryResponse])
async def list_user_inventory(
    product_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_equipped: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List user's inventory with filtering options"""
    try:
        stmt = (
            select(UserInventory)
            .where(UserInventory.user_id == user.user_id)
            .options(selectinload(UserInventory.product))
            .order_by(UserInventory.acquired_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        if is_equipped is not None:
            stmt = stmt.where(UserInventory.is_equipped == is_equipped)
            
        # Filter by product attributes if specified
        if product_type or category:
            stmt = stmt.join(Product)
            if product_type:
                stmt = stmt.where(Product.product_type == product_type)
            if category:
                stmt = stmt.where(Product.category == category)
                
        result = await session.execute(stmt)
        inventory_items = result.scalars().all()
        return [UserInventoryResponse.model_validate(item, from_attributes=True) for item in inventory_items]
    except Exception:
        await session.rollback()
        raise


@router.get("/{inventory_id}", response_model=UserInventoryResponse)
async def get_inventory_item(
    inventory_id: UUID,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get a specific inventory item"""
    try:
        stmt = (
            select(UserInventory)
            .where(UserInventory.id == inventory_id, UserInventory.user_id == user.user_id)
            .options(selectinload(UserInventory.product))
        )
        result = await session.execute(stmt)
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
            
        return UserInventoryResponse.model_validate(item, from_attributes=True)
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise


@router.post("/", response_model=UserInventoryResponse, status_code=status.HTTP_201_CREATED)
async def add_to_inventory(
    body: UserInventoryCreate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Add a product to user's inventory (admin/system use)"""
    try:
        # Verify product exists
        product_stmt = select(Product).where(Product.id == body.product_id)
        product_result = await session.execute(product_stmt)
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
            
        # Check if user already owns this product
        existing_stmt = select(UserInventory).where(
            UserInventory.user_id == body.user_id,
            UserInventory.product_id == body.product_id
        )
        existing_result = await session.execute(existing_stmt)
        existing_item = existing_result.scalar_one_or_none()
        
        if existing_item:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already owns this product")
            
        # Create inventory item
        inventory_item = UserInventory(**body.model_dump())
        session.add(inventory_item)
        await session.commit()
        
        # Reload with product relationship
        stmt = (
            select(UserInventory)
            .where(UserInventory.id == inventory_item.id)
            .options(selectinload(UserInventory.product))
        )
        result = await session.execute(stmt)
        item = result.scalar_one()
        
        return UserInventoryResponse.model_validate(item, from_attributes=True)
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise


@router.patch("/{inventory_id}", response_model=UserInventoryResponse)
async def update_inventory_item(
    inventory_id: UUID,
    body: UserInventoryUpdate,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Update an inventory item (e.g., equip/unequip)"""
    try:
        stmt = (
            select(UserInventory)
            .where(UserInventory.id == inventory_id, UserInventory.user_id == user.user_id)
            .options(selectinload(UserInventory.product))
        )
        result = await session.execute(stmt)
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
            
        # Update fields
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
            
        # Update usage tracking if equipping
        if body.is_equipped is True:
            item.usage_count += 1
            item.last_used_at = datetime.now(timezone.utc)
            
        await session.commit()
        await session.refresh(item)
        return UserInventoryResponse.model_validate(item, from_attributes=True)
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise


@router.delete("/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_inventory(
    inventory_id: UUID,
    _: AuthUser = Depends(get_current_user),  # Admin only in production
    session: AsyncSession = Depends(get_db),
):
    """Remove an item from user's inventory (admin only)"""
    try:
        stmt = select(UserInventory).where(UserInventory.id == inventory_id)
        result = await session.execute(stmt)
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
            
        await session.delete(item)
        await session.commit()
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise


@router.post("/grant/{user_id}/{product_id}", response_model=UserInventoryResponse, status_code=status.HTTP_201_CREATED)
async def grant_product_to_user(
    user_id: UUID,
    product_id: UUID,
    acquisition_method: AcquisitionMethod = AcquisitionMethod.GIFT,
    _: AuthUser = Depends(get_current_user),  # Admin only
    session: AsyncSession = Depends(get_db),
):
    """Grant a product to a user (admin only)"""
    try:
        # Verify product exists
        product_stmt = select(Product).where(Product.id == product_id)
        product_result = await session.execute(product_stmt)
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
            
        # Check if user already owns this product
        existing_stmt = select(UserInventory).where(
            UserInventory.user_id == user_id,
            UserInventory.product_id == product_id
        )
        existing_result = await session.execute(existing_stmt)
        existing_item = existing_result.scalar_one_or_none()
        
        if existing_item:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already owns this product")
            
        # Create inventory item
        inventory_item = UserInventory(
            user_id=user_id,
            product_id=product_id,
            acquired_via=acquisition_method.value,
            item_metadata={"granted_by": "admin"}
        )
        session.add(inventory_item)
        await session.commit()
        
        # Reload with product relationship
        stmt = (
            select(UserInventory)
            .where(UserInventory.id == inventory_item.id)
            .options(selectinload(UserInventory.product))
        )
        result = await session.execute(stmt)
        item = result.scalar_one()
        
        return UserInventoryResponse.model_validate(item, from_attributes=True)
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise
