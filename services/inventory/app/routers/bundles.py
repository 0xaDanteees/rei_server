# bundles router - product bundle management

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..security import get_current_user, AuthUser
from ..db import get_db
from ..models import (
    ProductBundle,
    ProductBundleItem,
    Product,
    ProductBundleCreate,
    ProductBundleResponse,
    ProductStatus,
)

router = APIRouter()


@router.get("/", response_model=List[ProductBundleResponse])
async def list_bundles(
    status: Optional[ProductStatus] = Query(ProductStatus.ACTIVE),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List available product bundles"""
    try:
        stmt = (
            select(ProductBundle)
            .options(
                selectinload(ProductBundle.bundle_items).selectinload(ProductBundleItem.product)
            )
            .order_by(ProductBundle.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        if status:
            stmt = stmt.where(ProductBundle.status == status.value)
            
        result = await session.execute(stmt)
        bundles = result.scalars().all()
        
        # Format response with bundle items
        response_bundles = []
        for bundle in bundles:
            bundle_dict = {
                "id": bundle.id,
                "name": bundle.name,
                "description": bundle.description,
                "price_usd": bundle.price_usd,
                "discount_percentage": bundle.discount_percentage,
                "image_url": bundle.image_url,
                "tags": bundle.tags,
                "status": bundle.status,
                "available_from": bundle.available_from,
                "available_until": bundle.available_until,
                "created_at": bundle.created_at,
                "updated_at": bundle.updated_at,
                "bundle_items": [
                    {
                        "product_id": item.product_id,
                        "product_name": item.product.name,
                        "quantity": item.quantity,
                        "is_featured": item.is_featured,
                        "rarity": item.product.rarity,
                        "category": item.product.category,
                    }
                    for item in bundle.bundle_items
                ]
            }
            response_bundles.append(bundle_dict)
            
        return response_bundles
    except Exception:
        await session.rollback()
        raise


@router.get("/{bundle_id}", response_model=ProductBundleResponse)
async def get_bundle(
    bundle_id: UUID,
    _: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get a specific bundle by ID"""
    try:
        stmt = (
            select(ProductBundle)
            .where(ProductBundle.id == bundle_id)
            .options(
                selectinload(ProductBundle.bundle_items).selectinload(ProductBundleItem.product)
            )
        )
        result = await session.execute(stmt)
        bundle = result.scalar_one_or_none()
        
        if not bundle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bundle not found")
            
        # Format response with bundle items
        bundle_dict = {
            "id": bundle.id,
            "name": bundle.name,
            "description": bundle.description,
            "price_usd": bundle.price_usd,
            "discount_percentage": bundle.discount_percentage,
            "image_url": bundle.image_url,
            "tags": bundle.tags,
            "status": bundle.status,
            "available_from": bundle.available_from,
            "available_until": bundle.available_until,
            "created_at": bundle.created_at,
            "updated_at": bundle.updated_at,
            "bundle_items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product.name,
                    "quantity": item.quantity,
                    "is_featured": item.is_featured,
                    "rarity": item.product.rarity,
                    "category": item.product.category,
                    "price_usd": item.product.price_usd,
                }
                for item in bundle.bundle_items
            ]
        }
        
        return bundle_dict
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise


@router.post("/", response_model=ProductBundleResponse, status_code=status.HTTP_201_CREATED)
async def create_bundle(
    body: ProductBundleCreate,
    _: AuthUser = Depends(get_current_user),  # Admin only in production
    session: AsyncSession = Depends(get_db),
):
    """Create a new product bundle (admin only)"""
    try:
        # Verify all products exist
        product_ids = body.product_ids
        products_stmt = select(Product).where(Product.id.in_(product_ids))
        products_result = await session.execute(products_stmt)
        products = products_result.scalars().all()
        
        if len(products) != len(product_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more products not found")
            
        # Create bundle
        bundle_data = body.model_dump(exclude={"product_ids"})
        bundle = ProductBundle(**bundle_data)
        session.add(bundle)
        await session.flush()  # Get bundle ID
        
        # Create bundle items
        for product_id in product_ids:
            bundle_item = ProductBundleItem(
                bundle_id=bundle.id,
                product_id=product_id,
                quantity=1,
                is_featured=False
            )
            session.add(bundle_item)
            
        await session.commit()
        
        # Reload with relationships
        stmt = (
            select(ProductBundle)
            .where(ProductBundle.id == bundle.id)
            .options(
                selectinload(ProductBundle.bundle_items).selectinload(ProductBundleItem.product)
            )
        )
        result = await session.execute(stmt)
        bundle = result.scalar_one()
        
        # Format response
        bundle_dict = {
            "id": bundle.id,
            "name": bundle.name,
            "description": bundle.description,
            "price_usd": bundle.price_usd,
            "discount_percentage": bundle.discount_percentage,
            "image_url": bundle.image_url,
            "tags": bundle.tags,
            "status": bundle.status,
            "available_from": bundle.available_from,
            "available_until": bundle.available_until,
            "created_at": bundle.created_at,
            "updated_at": bundle.updated_at,
            "bundle_items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product.name,
                    "quantity": item.quantity,
                    "is_featured": item.is_featured,
                    "rarity": item.product.rarity,
                    "category": item.product.category,
                }
                for item in bundle.bundle_items
            ]
        }
        
        return bundle_dict
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise


@router.patch("/{bundle_id}", response_model=ProductBundleResponse)
async def update_bundle(
    bundle_id: UUID,
    body: dict,  # Flexible update body
    _: AuthUser = Depends(get_current_user),  # Admin only in production
    session: AsyncSession = Depends(get_db),
):
    """Update a bundle (admin only)"""
    try:
        stmt = select(ProductBundle).where(ProductBundle.id == bundle_id)
        result = await session.execute(stmt)
        bundle = result.scalar_one_or_none()
        
        if not bundle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bundle not found")
            
        # Update allowed fields
        allowed_fields = {"name", "description", "price_usd", "discount_percentage", "status", "image_url", "tags"}
        for field, value in body.items():
            if field in allowed_fields:
                setattr(bundle, field, value)
                
        await session.commit()
        
        # Reload with relationships
        stmt = (
            select(ProductBundle)
            .where(ProductBundle.id == bundle.id)
            .options(
                selectinload(ProductBundle.bundle_items).selectinload(ProductBundleItem.product)
            )
        )
        result = await session.execute(stmt)
        bundle = result.scalar_one()
        
        # Format response
        bundle_dict = {
            "id": bundle.id,
            "name": bundle.name,
            "description": bundle.description,
            "price_usd": bundle.price_usd,
            "discount_percentage": bundle.discount_percentage,
            "image_url": bundle.image_url,
            "tags": bundle.tags,
            "status": bundle.status,
            "available_from": bundle.available_from,
            "available_until": bundle.available_until,
            "created_at": bundle.created_at,
            "updated_at": bundle.updated_at,
            "bundle_items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product.name,
                    "quantity": item.quantity,
                    "is_featured": item.is_featured,
                    "rarity": item.product.rarity,
                    "category": item.product.category,
                }
                for item in bundle.bundle_items
            ]
        }
        
        return bundle_dict
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise


@router.delete("/{bundle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bundle(
    bundle_id: UUID,
    _: AuthUser = Depends(get_current_user),  # Admin only in production
    session: AsyncSession = Depends(get_db),
):
    """Delete a bundle (admin only)"""
    try:
        stmt = select(ProductBundle).where(ProductBundle.id == bundle_id)
        result = await session.execute(stmt)
        bundle = result.scalar_one_or_none()
        
        if not bundle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bundle not found")
            
        await session.delete(bundle)
        await session.commit()
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise
