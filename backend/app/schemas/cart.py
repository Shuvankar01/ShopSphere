"""Cart Pydantic schemas using Decimal for monetary values."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from decimal import Decimal
from app.schemas.product import ProductResponse


class CartItemAdd(BaseModel):
    product_id: str
    quantity: int = 1


class CartItemUpdate(BaseModel):
    product_id: str
    quantity: int


class CartItemResponse(BaseModel):
    id: str
    product_id: str
    product: ProductResponse
    quantity: int
    unit_price: Decimal

    model_config = ConfigDict(from_attributes=True)


class CartResponse(BaseModel):
    id: str
    user_id: str
    items: List[CartItemResponse]
    subtotal: Decimal
    discount_amount: Decimal = Decimal("0.00")
    total: Decimal = Decimal("0.00")
    coupon_code: Optional[str] = None
    item_count: int = 0

    model_config = ConfigDict(from_attributes=True)
