"""MockPaymentProvider — DEMO-only payment simulation.

No real gateway, keys, webhooks, or transactions are ever involved. The
provider models the classic provider lifecycle (created -> pending -> settled /
failed / cancelled, plus refunds) with locally generated references, so the
rest of the app exercises the same state discipline a real integration would —
without touching the network.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal, Optional

from app.core.exceptions import BadRequestException

# Provider-controlled states (subset of schemas.payment.PAYMENT_TRANSITIONS).
CHARGE_STATES = ("pending", "succeeded", "failed", "cancelled")
REFUND_STATES = ("requested", "pending", "completed", "failed")


class MockPaymentProvider:
    """Simulates payment creation, settlement, failure, cancellation and refunds.

    Instances are stateless; every method is deterministic given its inputs and
    only generates references / validates state — actual rows are written by the
    PaymentRepository inside the caller's transaction.
    """

    name = "DEMO"

    def create_charge(
        self, *, order_id: str, amount: Decimal, currency: str, reference: str
    ) -> dict:
        """Initiate a demo payment -> returns a pending charge descriptor."""
        self._validate_amount(amount)
        return {
            "provider": self.name,
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "transaction_id": reference,
            "status": "pending",
        }

    def settle(self, *, transaction_id: str) -> str:
        """Simulate the provider settling a pending charge as success."""
        return "succeeded"

    def fail(self, *, transaction_id: str) -> str:
        return "failed"

    def cancel(self, *, transaction_id: str) -> str:
        return "cancelled"

    def create_refund(
        self, *, payment_reference: str, amount: Decimal, reference: str
    ) -> dict:
        self._validate_amount(amount)
        return {
            "provider": self.name,
            "payment_reference": payment_reference,
            "amount": amount,
            "refund_reference": reference,
            "status": "requested",
        }

    def complete_refund(self, *, reference: str) -> str:
        return "completed"

    @staticmethod
    def reference(prefix: str = "demo") -> str:
        return f"{prefix}_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def _validate_amount(amount: Decimal) -> None:
        if amount is None or Decimal(amount) <= 0:
            raise BadRequestException("Payment amount must be positive")

    @staticmethod
    def assert_charge_state(current: str, target: Literal["succeeded", "failed", "cancelled"]) -> None:
        """Mirror of the state machine used both by the API and the demo webhook."""
        if current not in CHARGE_STATES:
            raise BadRequestException(f"Invalid payment state '{current}'")
        if current == target:
            raise BadRequestException(f"Payment is already {target}")