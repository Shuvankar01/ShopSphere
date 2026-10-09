"""Return (RMA) schemas. Return state is kept SEPARATE from payment state."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Controlled return lifecycle.
RETURN_STATUSES = {
    "requested",
    "approved",
    "rejected",
    "received",
    "completed",
    "cancelled",
}

RETURN_TRANSITIONS = {
    "requested": {"approved", "rejected", "cancelled"},
    "approved": {"received", "cancelled"},
    "received": {"completed"},
    "completed": set(),
    "rejected": set(),
    "cancelled": set(),
}


class ReturnItemCreate(BaseModel):
    order_item_id: str
    quantity: int
    reason: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v


class ReturnCreate(BaseModel):
    order_id: str
    reason: str = Field(min_length=5, max_length=2000)
    items: List[ReturnItemCreate] = Field(min_length=1, max_length=50)


class ReturnItemResponse(BaseModel):
    id: str
    order_item_id: str
    quantity: int
    reason: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ReturnResponse(BaseModel):
    id: str
    order_id: str
    user_id: str
    status: str
    reason: str
    items: List[ReturnItemResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ReturnActionRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=1000)