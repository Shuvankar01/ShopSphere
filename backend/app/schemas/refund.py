"""Demo refund schemas. Refunds are bound to a captured Payment and never
exceed the captured amount; they carry their own status and are idempotent."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RefundCreate(BaseModel):
    order_id: str
    amount: Decimal
    reason: Optional[str] = Field(default=None, max_length=1000)
    idempotency_key: Optional[str] = Field(default=None, max_length=100)

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Refund amount must be positive")
        return v


class RefundResponse(BaseModel):
    id: str
    payment_id: str
    order_id: str
    amount: Decimal
    status: str
    reason: Optional[str] = None
    idempotency_key: Optional[str] = None
    provider_reference: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)