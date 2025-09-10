# products router

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from ..security import get_current_user, AuthUser
from ..db import get_db
from ..models import (
    Product,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductType,
    ProductCategory,
    ProductRarity,
    AcquisitionMethod,
    ProductStatus,
)

router = APIRouter()


@router.get("/", response_model=List[ProductResponse])
async def list_products(
    product_type: Optional[ProductType] = Query(None),
    category: Optional[ProductCategory] = Query(None),
    rarity: Optional[ProductRarity] = Query(None),
    acquisition_method: Optional[AcquisitionMethod] = Query(None),
    status: Optional[ProductStatus] = Query(ProductStatus.ACTIVE),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List products with filtering options"""
    try:
        stmt = select(Product).order_by(Product.created_at.desc()).limit(limit).offset(offset)
        
        if product_type:
            stmt = stmt.where(Product.product_type == product_type.value)
        if category:
            stmt = stmt.where(Product.category == category.value)
        if rarity:
            stmt = stmt.where(Product.rarity == rarity.value)
        if acquisition_method:
            stmt = stmt.where(Product.acquisition_method == acquisition_method.value)
        if status:
            stmt = stmt.where(Product.status == status.value)
            
        result = await session.execute(stmt)
        products = result.scalars().all()
        return [ProductResponse.model_validate(p, from_attributes=True) for p in products]
    except Exception:
        await session.rollback()
        raise


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    _: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get a specific product by ID"""
    try:
        stmt = select(Product).where(Product.id == product_id)
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
            
        return ProductResponse.model_validate(product, from_attributes=True)
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    _: AuthUser = Depends(get_current_user),  # Admin only in production
    session: AsyncSession = Depends(get_db),
):
    """Create a new product (admin only)"""
    try:
        product = Product(**body.model_dump())
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return ProductResponse.model_validate(product, from_attributes=True)
    except Exception:
        await session.rollback()
        raise


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    body: ProductUpdate,
    _: AuthUser = Depends(get_current_user),  # Admin only in production
    session: AsyncSession = Depends(get_db),
):
    """Update a product (admin only)"""
    try:
        stmt = select(Product).where(Product.id == product_id)
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
            
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
            
        await session.commit()
        await session.refresh(product)
        return ProductResponse.model_validate(product, from_attributes=True)
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    _: AuthUser = Depends(get_current_user),  # Admin only in production
    session: AsyncSession = Depends(get_db),
):
    """Delete a product (admin only)"""
    try:
        stmt = select(Product).where(Product.id == product_id)
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
            
        await session.delete(product)
        await session.commit()
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise


@router.get("/categories/list")
async def list_categories(
    _: AuthUser = Depends(get_current_user),
):
    """List all available product categories"""
    return {
        "product_types": [{"value": pt.value, "name": pt.value.replace("_", " ").title()} for pt in ProductType],
        "categories": [{"value": cat.value, "name": cat.value.replace("_", " ").title()} for cat in ProductCategory],
        "rarities": [{"value": r.value, "name": r.value.title()} for r in ProductRarity],
        "acquisition_methods": [{"value": am.value, "name": am.value.replace("_", " ").title()} for am in AcquisitionMethod],
    }
