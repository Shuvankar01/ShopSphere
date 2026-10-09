"""Payment schemas — server-side validation of DEMO payments.

No real gateway is involved. The server creates a pending demo transaction and
only settles it after the frontend performs a demo success/failure action that
the server re-validates (ownership, order, amount, currency, allowed state).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.order import ALLOWED_PAYMENT_METHODS

# Controlled demo payment status lifecycle.
PAYMENT_TRANSITIONS = {
    "pending": {"succeeded", "failed", "cancelled"},
    "succeeded": {"refund_pending", "refunded", "partially_refunded"},
    "refund_pending": {"refunded", "partially_refunded", "failed"},
    "failed": {"pending"},
    "cancelled": {"pending"},
    "refunded": set(),
    "partially_refunded": {"refunded"},
}

# Demo webhook event names (local only — no provider signature verification).
WEBHOOK_EVENTS = {
    "payment.succeeded",
    "payment.failed",
    "payment.cancelled",
    "refund.pending",
    "refund.completed",
    "refund.failed",
}


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
    provider: str = "DEMO"
    order_id: str
    amount: Decimal
    currency: str
    redirect_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentCompleteRequest(BaseModel):
    """Frontend performs a demo action on an existing pending transaction."""

    result: Literal["success", "failure", "cancel"]


class WebhookEvent(BaseModel):
    """Demo webhook event. `transaction_id` is the DEMO transaction reference
    (or DEMO refund reference). Idempotent: re-delivering an event whose target
    state is already reached is a no-op."""

    transaction_id: str
    event: str
    amount: Optional[Decimal] = None

    @field_validator("event")
    @classmethod
    def valid_event(cls, v: str) -> str:
        if v not in WEBHOOK_EVENTS:
            raise ValueError(f"event must be one of {sorted(WEBHOOK_EVENTS)}")
        return v