# purchases router - purchase history and transactions

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..security import get_current_user, AuthUser
from ..db import get_db
from ..models import (
    UserPurchase,
    Product,
    ProductBundle,
    UserInventory,
    UserPurchaseCreate,
    UserPurchaseResponse,
    AcquisitionMethod,
)

router = APIRouter()


@router.get("/", response_model=List[UserPurchaseResponse])
async def list_user_purchases(
    purchase_status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List user's purchase history"""
    try:
        stmt = (
            select(UserPurchase)
            .where(UserPurchase.user_id == user.user_id)
            .order_by(UserPurchase.purchased_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        if purchase_status:
            stmt = stmt.where(UserPurchase.status == purchase_status)
            
        result = await session.execute(stmt)
        purchases = result.scalars().all()
        return [UserPurchaseResponse.model_validate(p, from_attributes=True) for p in purchases]
    except Exception:
        await session.rollback()
        raise


@router.get("/{purchase_id}", response_model=UserPurchaseResponse)
async def get_purchase(
    purchase_id: UUID,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get a specific purchase"""
    try:
        stmt = select(UserPurchase).where(
            UserPurchase.id == purchase_id,
            UserPurchase.user_id == user.user_id
        )
        result = await session.execute(stmt)
        purchase = result.scalar_one_or_none()
        
        if not purchase:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found")
            
        return UserPurchaseResponse.model_validate(purchase, from_attributes=True)
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise


@router.post("/product/{product_id}", response_model=UserPurchaseResponse, status_code=status.HTTP_201_CREATED)
async def purchase_product(
    product_id: UUID,
    payment_method: Optional[str] = "stripe",
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Purchase a single product"""
    try:
        # Verify product exists and is purchasable
        product_stmt = select(Product).where(Product.id == product_id)
        product_result = await session.execute(product_stmt)
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
            
        if product.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product not available for purchase")
            
        if product.acquisition_method != "purchase":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product not available for purchase")
            
        if not product.price_usd or product.price_usd <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product price not set")
            
        # Check if user already owns this product
        existing_stmt = select(UserInventory).where(
            UserInventory.user_id == user.user_id,
            UserInventory.product_id == product_id
        )
        existing_result = await session.execute(existing_stmt)
        existing_item = existing_result.scalar_one_or_none()
        
        if existing_item:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already owns this product")
            
        # Create purchase record
        purchase = UserPurchase(
            user_id=user.user_id,
            product_id=product_id,
            amount_usd=product.price_usd,
            payment_method=payment_method,
            status="pending"
        )
        session.add(purchase)
        await session.flush()  # Get purchase ID
        
        # In a real implementation, you would integrate with payment processor here
        # For MVP, we'll simulate successful payment
        purchase.status = "completed"
        purchase.transaction_id = f"sim_{purchase.id.hex[:8]}"
        purchase.processed_at = datetime.now(timezone.utc)
        
        # Add product to user's inventory
        inventory_item = UserInventory(
            user_id=user.user_id,
            product_id=product_id,
            acquired_via=AcquisitionMethod.PURCHASE.value,
            item_metadata={"purchase_id": str(purchase.id)}
        )
        session.add(inventory_item)
        
        await session.commit()
        await session.refresh(purchase)
        
        return UserPurchaseResponse.model_validate(purchase, from_attributes=True)
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise


@router.post("/bundle/{bundle_id}", response_model=UserPurchaseResponse, status_code=status.HTTP_201_CREATED)
async def purchase_bundle(
    bundle_id: UUID,
    payment_method: Optional[str] = "stripe",
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Purchase a product bundle"""
    try:
        # Verify bundle exists and is purchasable
        bundle_stmt = (
            select(ProductBundle)
            .where(ProductBundle.id == bundle_id)
            .options(selectinload(ProductBundle.bundle_items))
        )
        bundle_result = await session.execute(bundle_stmt)
        bundle = bundle_result.scalar_one_or_none()
        
        if not bundle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bundle not found")
            
        if bundle.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bundle not available for purchase")
            
        # Check if user already owns any products in the bundle
        product_ids = [item.product_id for item in bundle.bundle_items]
        existing_stmt = select(UserInventory).where(
            UserInventory.user_id == user.user_id,
            UserInventory.product_id.in_(product_ids)
        )
        existing_result = await session.execute(existing_stmt)
        existing_items = existing_result.scalars().all()
        
        if existing_items:
            owned_products = [str(item.product_id) for item in existing_items]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=f"User already owns some products in this bundle: {owned_products}"
            )
            
        # Create purchase record
        purchase = UserPurchase(
            user_id=user.user_id,
            bundle_id=bundle_id,
            amount_usd=bundle.price_usd,
            payment_method=payment_method,
            status="pending"
        )
        session.add(purchase)
        await session.flush()  # Get purchase ID
        
        # In a real implementation, you would integrate with payment processor here
        # For MVP, we'll simulate successful payment
        purchase.status = "completed"
        purchase.transaction_id = f"sim_{purchase.id.hex[:8]}"
        purchase.processed_at = datetime.now(timezone.utc)
        
        # Add all bundle products to user's inventory
        for item in bundle.bundle_items:
            inventory_item = UserInventory(
                user_id=user.user_id,
                product_id=item.product_id,
                acquired_via=AcquisitionMethod.PURCHASE.value,
                item_metadata={"purchase_id": str(purchase.id), "bundle_id": str(bundle_id)}
            )
            session.add(inventory_item)
        
        await session.commit()
        await session.refresh(purchase)
        
        return UserPurchaseResponse.model_validate(purchase, from_attributes=True)
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise


@router.post("/{purchase_id}/refund", response_model=UserPurchaseResponse)
async def refund_purchase(
    purchase_id: UUID,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Request a refund for a purchase (admin approval required)"""
    try:
        stmt = select(UserPurchase).where(
            UserPurchase.id == purchase_id,
            UserPurchase.user_id == user.user_id
        )
        result = await session.execute(stmt)
        purchase = result.scalar_one_or_none()
        
        if not purchase:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found")
            
        if purchase.status != "completed":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only refund completed purchases")
            
        # In a real implementation, you would integrate with payment processor
        # For MVP, we'll mark as refunded and remove from inventory
        purchase.status = "refunded"
        
        # Remove products from user's inventory
        if purchase.product_id:
            inventory_stmt = select(UserInventory).where(
                UserInventory.user_id == user.user_id,
                UserInventory.product_id == purchase.product_id
            )
            inventory_result = await session.execute(inventory_stmt)
            inventory_item = inventory_result.scalar_one_or_none()
            if inventory_item:
                await session.delete(inventory_item)
                
        elif purchase.bundle_id:
            # Remove all bundle products from inventory
            bundle_stmt = (
                select(ProductBundle)
                .where(ProductBundle.id == purchase.bundle_id)
                .options(selectinload(ProductBundle.bundle_items))
            )
            bundle_result = await session.execute(bundle_stmt)
            bundle = bundle_result.scalar_one_or_none()
            
            if bundle:
                product_ids = [item.product_id for item in bundle.bundle_items]
                inventory_stmt = select(UserInventory).where(
                    UserInventory.user_id == user.user_id,
                    UserInventory.product_id.in_(product_ids)
                )
                inventory_result = await session.execute(inventory_stmt)
                inventory_items = inventory_result.scalars().all()
                
                for item in inventory_items:
                    await session.delete(item)
        
        await session.commit()
        await session.refresh(purchase)
        
        return UserPurchaseResponse.model_validate(purchase, from_attributes=True)
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise
