"""Order Pydantic schemas with state machine and Decimal pricing."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

ORDER_STATUSES = {"pending", "confirmed", "shipped", "delivered", "cancelled"}
PAYMENT_STATUSES = {"pending", "paid", "failed", "refunded"}

# Single source of truth for payment methods accepted by the API.
# Includes the methods the checkout UI offers (card / paypal / cod).
ALLOWED_PAYMENT_METHODS = {"card", "paypal", "cod", "upi", "netbanking", "wallet"}


class OrderCreate(BaseModel):
    shipping_address: str = Field(max_length=1000)
    payment_method: str = "card"

    @field_validator("payment_method")
    @classmethod
    def valid_payment_method(cls, v: str) -> str:
        if v not in ALLOWED_PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {ALLOWED_PAYMENT_METHODS}")
        return v


class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    quantity: int
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: str
    user_id: str
    items: List[OrderItemResponse]
    total_amount: Decimal
    order_status: str
    payment_status: str
    payment_method: str
    shipping_address: str
    coupon_id: Optional[str] = None
    discount_amount: Decimal = Decimal("0.00")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in ORDER_STATUSES:
            raise ValueError(f"status must be one of {sorted(ORDER_STATUSES)}")
        return v
