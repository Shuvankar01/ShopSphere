"""Order Pydantic schemas with the controlled state machine and Decimal pricing.

All money fields are Decimals and serialize as JSON strings on the wire — the
frontend must never compute or supply order totals.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Controlled order lifecycle. Transitions are enforced in
# order_service.VALID_TRANSITIONS.
ORDER_STATUSES = {
    "pending",
    "confirmed",
    "processing",
    "packed",
    "shipped",
    "out_for_delivery",
    "delivered",
    "cancelled",
}

# Order-level payment status is kept SEPARATE from order status.
PAYMENT_STATUSES = {"pending", "paid", "failed", "refunded", "partially_refunded"}

# Single source of truth for payment methods accepted by the API.
# (DEMO only — no real gateway is ever contacted.)
ALLOWED_PAYMENT_METHODS = {"card", "paypal", "cod", "upi", "netbanking", "wallet"}

# Demo shipping methods (see app.services.shipping). "standard" is the default.
DEFAULT_SHIPPING_METHOD = "standard"
SHIPPING_METHODS = {"standard", "express", "priority"}


class OrderCreate(BaseModel):
    """Checkout request. The backend computes every total; the client only
    supplies the shipping address (either a saved address id or free text) and
    the chosen shipping/payment methods."""

    shipping_address: Optional[str] = Field(default=None, max_length=1000)
    shipping_address_id: Optional[str] = None
    shipping_method: str = DEFAULT_SHIPPING_METHOD
    payment_method: str = "card"

    @field_validator("shipping_method")
    @classmethod
    def valid_shipping_method(cls, v: str) -> str:
        if v not in SHIPPING_METHODS:
            raise ValueError(f"shipping_method must be one of {sorted(SHIPPING_METHODS)}")
        return v

    @field_validator("payment_method")
    @classmethod
    def valid_payment_method(cls, v: str) -> str:
        if v not in ALLOWED_PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {ALLOWED_PAYMENT_METHODS}")
        return v

    @model_validator(mode="after")
    def exactly_one_address(self):
        if not self.shipping_address and not self.shipping_address_id:
            raise ValueError("Either shipping_address or shipping_address_id is required")
        if self.shipping_address and self.shipping_address_id:
            raise ValueError("Provide exactly one of shipping_address / shipping_address_id")
        return self


class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    quantity: int
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderStatusHistoryResponse(BaseModel):
    from_status: Optional[str] = None
    to_status: str
    changed_by: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CheckoutQuoteRequest(BaseModel):
    """Pre-checkout pricing request. Only the shipping method is supplied — the
    backend recomputes every amount from the cart and current coupon."""

    shipping_method: str = DEFAULT_SHIPPING_METHOD

    @field_validator("shipping_method")
    @classmethod
    def valid_shipping_method(cls, v: str) -> str:
        if v not in SHIPPING_METHODS:
            raise ValueError(f"shipping_method must be one of {sorted(SHIPPING_METHODS)}")
        return v


class CheckoutQuoteResponse(BaseModel):
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    shipping_cost: Decimal
    total_amount: Decimal
    shipping_method: str
    shipping_method_name: str
    estimated_delivery: str
    coupon_code: Optional[str] = None
    currency: str


class OrderResponse(BaseModel):
    id: str
    user_id: str
    items: List[OrderItemResponse]
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    shipping_cost: Decimal
    total_amount: Decimal
    order_status: str
    payment_status: str
    payment_method: str
    shipping_method: str
    shipping_address: str
    shipping_address_snapshot: Optional[str] = None
    tracking_number: Optional[str] = None
    shipment_status: str
    coupon_id: Optional[str] = None
    status_history: List[OrderStatusHistoryResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in ORDER_STATUSES:
            raise ValueError(f"status must be one of {sorted(ORDER_STATUSES)}")
        return v