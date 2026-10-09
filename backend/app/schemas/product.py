"""Product-domain Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Brand
# ---------------------------------------------------------------------------

class BrandCreate(BaseModel):
    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: Optional[bool] = None


class BrandResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Product Image
# ---------------------------------------------------------------------------

class ProductImageResponse(BaseModel):
    id: str
    product_id: str
    url: str
    alt_text: Optional[str] = None
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class ProductImageCreate(BaseModel):
    url: str
    alt_text: Optional[str] = None
    sort_order: int = 0


# ---------------------------------------------------------------------------
# Product Variant
# ---------------------------------------------------------------------------

class ProductVariantCreate(BaseModel):
    sku: str
    name: str
    price_override: Optional[Decimal] = None
    stock: int = 0
    attributes: Optional[str] = None  # JSON string


class ProductVariantUpdate(BaseModel):
    name: Optional[str] = None
    price_override: Optional[Decimal] = None
    stock: Optional[int] = None
    attributes: Optional[str] = None
    is_active: Optional[bool] = None


class ProductVariantResponse(BaseModel):
    id: str
    product_id: str
    sku: str
    name: str
    price_override: Optional[Decimal] = None
    stock: int
    attributes: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class ProductBase(BaseModel):
    name: str
    description: str
    sku: Optional[str] = None
    price: Decimal
    discount_price: Optional[Decimal] = None
    stock: int = 0
    image_url: Optional[str] = None
    specifications: Optional[str] = None  # JSON string of key/value specs
    category_id: str
    brand_id: Optional[str] = None

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Price must be greater than zero")
        return v

    @field_validator("discount_price")
    @classmethod
    def discount_must_be_less(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        if v is not None and "price" in info.data and v >= info.data["price"]:
            raise ValueError("Discount price must be less than price")
        return v


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[Decimal] = None
    discount_price: Optional[Decimal] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None
    specifications: Optional[str] = None
    category_id: Optional[str] = None
    brand_id: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str
    sku: Optional[str] = None
    price: Decimal
    discount_price: Optional[Decimal] = None
    stock: int
    image_url: Optional[str] = None
    specifications: Optional[str] = None
    category_id: str
    brand_id: Optional[str] = None
    seller_id: str
    is_active: bool
    created_at: datetime
    rating: Optional[Decimal] = None
    review_count: int = 0
    category: Optional[CategoryResponse] = None
    brand: Optional[BrandResponse] = None
    images: List[ProductImageResponse] = []
    variants: List[ProductVariantResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PaginatedProducts(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    limit: int


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------

class ReviewCreate(BaseModel):
    rating: int
    comment: str
    # Optional already-uploaded image URLs (via the product image upload flow).
    image_urls: List[str] = []

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v: int) -> int:
        if not (1 <= v <= 5):
            raise ValueError("Rating must be between 1 and 5")
        return v

    @field_validator("image_urls")
    @classmethod
    def limit_images(cls, v: List[str]) -> List[str]:
        if len(v) > 5:
            raise ValueError("A review can have at most 5 images")
        return v


class ReviewImageResponse(BaseModel):
    id: str
    url: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class ReviewResponse(BaseModel):
    id: str
    user_id: str
    user_name: str
    product_id: str
    rating: int
    comment: str
    is_verified: bool = False
    moderation_status: str = "approved"
    images: List[ReviewImageResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewModerationUpdate(BaseModel):
    action: str  # approve / reject

    @field_validator("action")
    @classmethod
    def valid_action(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("action must be 'approve' or 'reject'")
        return v
