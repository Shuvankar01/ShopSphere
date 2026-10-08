"""Wishlist Pydantic schemas."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import datetime
from app.schemas.product import ProductResponse


class WishlistItemResponse(BaseModel):
    id: str
    product_id: str
    product: ProductResponse
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WishlistResponse(BaseModel):
    id: str
    user_id: str
    items: List[WishlistItemResponse]

    model_config = ConfigDict(from_attributes=True)


class WishlistAddItem(BaseModel):
    product_id: str


class MoveToCart(BaseModel):
    product_id: str
    quantity: int = 1
