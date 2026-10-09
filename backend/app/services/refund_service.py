"""Refund service — DEMO refunds bound to captured payments.

Rules: a refund belongs to an existing captured Payment, never exceeds the
captured demo amount, carries its own status, is idempotent (idempotency_key),
and updates the payment/order states consistently. No real money is involved.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.logging import logger
from app.models.payment import Refund
from app.models.user import User
from app.repositories.order_repo import OrderRepository
from app.repositories.payment_repo import PaymentRepository
from app.schemas.refund import RefundCreate, RefundResponse
from app.services.mock_payment_provider import MockPaymentProvider


class RefundService:
    def __init__(
        self,
        order_repo: OrderRepository,
        payment_repo: PaymentRepository,
    ):
        self.order_repo = order_repo
        self.payment_repo = payment_repo
        self.provider = MockPaymentProvider()

    def _require_admin(self, user: User) -> None:
        if user.role != "admin":
            raise ForbiddenException("Only admins can issue refunds")

    def _captured_payment(self, order_id: str):
        """The succeeded DEMO capture for an order (refunds attach to it)."""
        for payment in self.payment_repo.get_payments_for_order(order_id):
            if payment.status == "succeeded":
                return payment
        return None

    def create_refund(
        self, data: RefundCreate, current_user: User
    ) -> RefundResponse:
        self._require_admin(current_user)

        order = self.order_repo.get_order(data.order_id)
        if not order:
            raise NotFoundException("Order not found")

        if data.idempotency_key:
            existing = self.payment_repo.get_refund_by_idempotency_key(
                data.idempotency_key
            )
            if existing:
                if existing.order_id != order.id:
                    raise BadRequestException("Idempotency key already used for another order")
                return RefundResponse.model_validate(existing)

        payment = self._captured_payment(order.id)
        if payment is None:
            raise BadRequestException("Order has no captured payment to refund")

        refunded = self.payment_repo.refunded_total(payment)
        remaining = Decimal(str(payment.amount)) - Decimal(str(refunded))
        amount = Decimal(str(data.amount)).quantize(Decimal("0.01"))
        if amount <= 0:
            raise BadRequestException("Refund amount must be positive")
        if amount > remaining:
            raise BadRequestException(
                f"Refund amount exceeds the captured balance (captured={payment.amount}, "
                f"already refunded={refunded})"
            )

        refund = self.payment_repo.create_refund(
            payment,
            amount=amount,
            reason=data.reason,
            idempotency_key=data.idempotency_key,
        )
        self.payment_repo.complete_refund(refund, payment, order)
        self.payment_repo.db.commit()

        logger.info(
            f"DEMO refund {refund.id} ({refund.provider_reference}) for order {order.id} "
            f"amount={amount} → completed"
        )
        return RefundResponse.model_validate(refund)

    def process_refund(self, refund_id: str, current_user: User) -> RefundResponse:
        """Idempotent demo processing step (also reachable via the demo webhook)."""
        self._require_admin(current_user)
        refund = self.payment_repo.get_refund(refund_id)
        if not refund:
            raise NotFoundException("Refund not found")
        if refund.status == "completed":
            return RefundResponse.model_validate(refund)  # idempotent
        if refund.status not in ("requested", "pending"):
            raise BadRequestException(f"Refund is in state '{refund.status}'")

        order = refund.payment.order if refund.payment else None
        if order is None:
            raise NotFoundException("Refund order not found")
        self.payment_repo.complete_refund(refund, refund.payment, order)
        self.payment_repo.db.commit()
        return RefundResponse.model_validate(refund)

    def list_refunds(self, current_user: User, order_id: str | None = None) -> List[RefundResponse]:
        self._require_admin(current_user)
        if order_id:
            refunds = self.payment_repo.get_refunds_for_order(order_id)
        else:
            refunds = self.payment_repo.get_all_refunds()
        return [RefundResponse.model_validate(r) for r in refunds]

    def get_refund(self, refund_id: str, current_user: User) -> RefundResponse:
        refund = self.payment_repo.get_refund(refund_id)
        if not refund:
            raise NotFoundException("Refund not found")
        return RefundResponse.model_validate(refund)