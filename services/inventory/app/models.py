from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4
import random

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, DateTime, Boolean, Float, Integer, Text, ForeignKey, Index, func, text, Table, event
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


# >w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨
#                       ENUMS
# >w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>


class ProductType(str, Enum):
    APPEARANCE = "appearance"      # Hair colors, skin tones, body shapes
    CLOTHING = "clothing"          # Tops, bottoms, dresses, shoes
    ACCESSORIES = "accessories"    # Piercings, tattoos, jewelry
    PERSONALITY = "personality"    # Personality traits
    CONSUMABLE = "consumable"      # Temporary boosts, gifts

class ProductCategory(str, Enum):
    # Appearance categories
    HAIR_COLOR = "hair_color"
    SKIN_TONE = "skin_tone"
    EYE_COLOR = "eye_color"
    BODY_SHAPE = "body_shape"
    FACE_SHAPE = "face_shape"
    
    # Clothing categories
    TOPS = "tops"
    BOTTOMS = "bottoms"
    DRESSES = "dresses"
    SHOES = "shoes"
    UNDERWEAR = "underwear"
    OUTERWEAR = "outerwear"
    
    # Accessory categories
    PIERCINGS = "piercings"
    TATTOOS = "tattoos"
    JEWELRY = "jewelry"
    MAKEUP = "makeup"
    
    # Personality categories
    SINGLE_TRAIT = "single_trait"         # Individual personality trait
    TRAIT_PACK = "trait_pack"             # Bundle of multiple traits
    PERSONALITY_PRESET = "personality_preset"
    
    # Consumable categories
    GIFT_BOX = "gift_box"
    BOOST_PACK = "boost_pack"

class ProductRarity(str, Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

class AcquisitionMethod(str, Enum):
    FREE = "free"              # Available from start
    PURCHASE = "purchase"      # Buy with real money
    EARN = "earn"             # Unlock through gameplay
    GIFT = "gift"             # Received as gift/reward
    RANDOM_DROP = "random_drop" # Random loot box/gacha

class ProductStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    SEASONAL = "seasonal"
    LIMITED = "limited"

# >w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>
#                       SQLALCHEMY MODELS
# >w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>

class Product(Base):
    """
    Master product catalog - all customization items available in the system
    """
    __tablename__ = "products"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    product_type = Column(String(32), nullable=False)  # ProductType enum
    category = Column(String(32), nullable=False)      # ProductCategory enum
    rarity = Column(String(16), nullable=False)        # ProductRarity enum
    
    # Pricing and availability
    price_usd = Column(Float, nullable=True)           # Real money price (USD)
    acquisition_method = Column(String(16), nullable=False)  # AcquisitionMethod enum
    status = Column(String(16), nullable=False, default="active")  # ProductStatus enum
    
    # Product attributes (flexible JSON for different product types)
    attributes = Column(JSONB, nullable=True)  # Color codes, sizes, trait values, etc.
    
    # Metadata
    image_url = Column(String(512), nullable=True)
    preview_url = Column(String(512), nullable=True)
    tags = Column(JSONB, nullable=True)  # Array of tags for filtering
    
    # Availability windows
    available_from = Column(DateTime(timezone=True), nullable=True)
    available_until = Column(DateTime(timezone=True), nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user_inventories = relationship("UserInventory", back_populates="product")
    
    __table_args__ = (
        Index("idx_products_type_category", product_type, category),
        Index("idx_products_rarity", rarity),
        Index("idx_products_acquisition", acquisition_method),
        Index("idx_products_status", status),
        Index("idx_products_created", created_at.desc()),
    )


class UserInventory(Base):
    """
    User's owned products - what each user has unlocked/purchased
    """
    __tablename__ = "user_inventories"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    
    # Acquisition details
    acquired_via = Column(String(16), nullable=False)  # AcquisitionMethod enum
    acquired_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Usage tracking
    is_equipped = Column(Boolean, default=False, nullable=False)  # Currently applied to partner
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    item_metadata = Column(JSONB, nullable=True)  # Custom data per user (e.g., purchase receipt)
    
    # Relationships
    product = relationship("Product", back_populates="user_inventories")
    
    __table_args__ = (
        Index("idx_user_inventory_user", user_id),
        Index("idx_user_inventory_product", product_id),
        Index("idx_user_inventory_equipped", user_id, is_equipped),
        Index("idx_user_inventory_acquired", acquired_at.desc()),
        # Unique constraint: user can only own each product once
        Index("idx_user_inventory_unique", user_id, product_id, unique=True),
    )


class ProductBundle(Base):
    """
    Product bundles/packs - collections of products sold together
    """
    __tablename__ = "product_bundles"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    
    # Pricing
    price_usd = Column(Float, nullable=False)
    discount_percentage = Column(Float, nullable=True)  # Discount vs individual prices
    
    # Bundle metadata
    image_url = Column(String(512), nullable=True)
    tags = Column(JSONB, nullable=True)
    
    # Availability
    status = Column(String(16), nullable=False, default="active")
    available_from = Column(DateTime(timezone=True), nullable=True)
    available_until = Column(DateTime(timezone=True), nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    bundle_items = relationship("ProductBundleItem", back_populates="bundle", cascade="all, delete-orphan")
    purchases = relationship("UserPurchase", back_populates="bundle")


class ProductBundleItem(Base):
    """
    Items within a product bundle
    """
    __tablename__ = "product_bundle_items"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    bundle_id = Column(PGUUID(as_uuid=True), ForeignKey("product_bundles.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    
    # Item details
    quantity = Column(Integer, default=1, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)  # Highlight in bundle display
    
    # Relationships
    bundle = relationship("ProductBundle", back_populates="bundle_items")
    product = relationship("Product")
    
    __table_args__ = (
        Index("idx_bundle_items_bundle", bundle_id),
        Index("idx_bundle_items_product", product_id),
    )


class UserPurchase(Base):
    """
    Purchase history - track what users have bought
    """
    __tablename__ = "user_purchases"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Purchase target (either individual product or bundle)
    product_id = Column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    bundle_id = Column(PGUUID(as_uuid=True), ForeignKey("product_bundles.id", ondelete="SET NULL"), nullable=True)
    
    # Transaction details
    amount_usd = Column(Float, nullable=False)
    currency = Column(String(8), default="USD", nullable=False)
    payment_method = Column(String(32), nullable=True)  # stripe, paypal, etc.
    transaction_id = Column(String(128), nullable=True)  # External payment ID
    
    # Status
    status = Column(String(16), nullable=False, default="pending")  # pending, completed, failed, refunded
    
    # Audit
    purchased_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    product = relationship("Product")
    bundle = relationship("ProductBundle", back_populates="purchases")
    
    __table_args__ = (
        Index("idx_purchases_user", user_id),
        Index("idx_purchases_status", status),
        Index("idx_purchases_date", purchased_at.desc()),
        Index("idx_purchases_transaction", transaction_id),
    )


# >w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>
#                       PYDANTIC SCHEMAS
# >w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    product_type: ProductType
    category: ProductCategory
    rarity: ProductRarity
    price_usd: Optional[float] = Field(None, ge=0)
    acquisition_method: AcquisitionMethod
    status: ProductStatus = ProductStatus.ACTIVE
    attributes: Optional[dict] = None
    image_url: Optional[str] = Field(None, max_length=512)
    preview_url: Optional[str] = Field(None, max_length=512)
    tags: Optional[List[str]] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    price_usd: Optional[float] = Field(None, ge=0)
    status: Optional[ProductStatus] = None
    attributes: Optional[dict] = None
    image_url: Optional[str] = Field(None, max_length=512)
    preview_url: Optional[str] = Field(None, max_length=512)
    tags: Optional[List[str]] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None


class ProductResponse(ProductBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserInventoryBase(BaseModel):
    acquired_via: AcquisitionMethod
    is_equipped: bool = False
    item_metadata: Optional[dict] = None


class UserInventoryCreate(UserInventoryBase):
    user_id: UUID
    product_id: UUID


class UserInventoryUpdate(BaseModel):
    is_equipped: Optional[bool] = None
    item_metadata: Optional[dict] = None


class UserInventoryResponse(UserInventoryBase):
    id: UUID
    user_id: UUID
    product_id: UUID
    acquired_at: datetime
    usage_count: int
    last_used_at: Optional[datetime]
    product: ProductResponse
    
    class Config:
        from_attributes = True


class ProductBundleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    price_usd: float = Field(..., ge=0)
    discount_percentage: Optional[float] = Field(None, ge=0, le=100)
    image_url: Optional[str] = Field(None, max_length=512)
    tags: Optional[List[str]] = None
    status: ProductStatus = ProductStatus.ACTIVE
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None


class ProductBundleCreate(ProductBundleBase):
    product_ids: List[UUID] = Field(..., min_items=1)


class ProductBundleResponse(ProductBundleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    bundle_items: List[dict] = []  # Will be populated with products
    
    class Config:
        from_attributes = True


class UserPurchaseBase(BaseModel):
    amount_usd: float = Field(..., ge=0)
    currency: str = Field(default="USD", max_length=8)
    payment_method: Optional[str] = Field(None, max_length=32)


class UserPurchaseCreate(UserPurchaseBase):
    user_id: UUID
    product_id: Optional[UUID] = None
    bundle_id: Optional[UUID] = None


class UserPurchaseResponse(UserPurchaseBase):
    id: UUID
    user_id: UUID
    product_id: Optional[UUID]
    bundle_id: Optional[UUID]
    transaction_id: Optional[str]
    status: str
    purchased_at: datetime
    processed_at: Optional[datetime]
    
    class Config:
        from_attributes = True