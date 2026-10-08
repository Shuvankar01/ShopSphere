"""Payment schemas — server-side validation of payment requests."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.order import ALLOWED_PAYMENT_METHODS


class PaymentCreate(BaseModel):
    order_id: str
    payment_method: str

    @field_validator("payment_method")
    @classmethod
    def valid_payment_method(cls, v: str) -> str:
        if v not in ALLOWED_PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {ALLOWED_PAYMENT_METHODS}")
        return v


class PaymentResponse(BaseModel):
    transaction_id: str
    status: str
    redirect_url: str | None = None

    model_config = ConfigDict(from_attributes=True)
