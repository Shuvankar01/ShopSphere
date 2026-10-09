"""Payment service — DEMO-only two-phase payment processing.

Phase 1: `create_payment` records a pending Payment + PaymentTransaction.
Phase 2: the frontend performs an explicit demo action (`complete_payment`) or
a local demo webhook delivers an event — the server re-validates the existing
transaction (ownership, order, amount, currency, allowed state) and only then
moves states. A client can never simply mark an order paid.
"""
from __future__ import annotations

from decimal import Decimal

from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from app.core.logging import logger
from app.models.payment import Payment
from app.models.user import User
from app.repositories.order_repo import OrderRepository
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import (
    PaymentCompleteRequest,
    PaymentCreate,
    PaymentResponse,
    WebhookEvent,
)
from app.services.mock_payment_provider import MockPaymentProvider


class PaymentService:
    def __init__(
        self,
        order_repo: OrderRepository,
        payment_repo: PaymentRepository,
    ):
        self.order_repo = order_repo
        self.payment_repo = payment_repo
        self.provider = MockPaymentProvider()

    # ------------------------------------------------------------------
    # Phase 1 — create the demo payment transaction
    # ------------------------------------------------------------------

    def create_payment(self, data: PaymentCreate, current_user: User) -> PaymentResponse:
        order = self.order_repo.get_order(data.order_id)
        # IDOR: a foreign order is indistinguishable from a missing one.
        if not order or order.user_id != current_user.id:
            raise NotFoundException("Order not found")

        if order.payment_status in ("paid", "refunded", "partially_refunded"):
            raise ConflictException("Order is already paid")
        if order.order_status == "cancelled":
            raise ConflictException("Order is cancelled and cannot be paid")
        if self._pending_payment_exists(order.id):
            raise ConflictException("A payment for this order is already in progress")

        payment, transaction = self.payment_repo.create_payment(
            order=order,
            user_id=current_user.id,
            payment_method=data.payment_method,
            amount=order.total_amount,
            currency=settings.CURRENCY,
        )
        self.payment_repo.db.commit()

        logger.info(
            f"DEMO payment {transaction.reference} created for order {order.id} "
            f"amount={order.total_amount} {settings.CURRENCY}"
        )
        return PaymentResponse(
            transaction_id=transaction.reference,
            status=payment.status,
            provider=self.provider.name,
            order_id=order.id,
            amount=order.total_amount,
            currency=payment.currency,
        )

    def _pending_payment_exists(self, order_id: str) -> bool:
        return any(
            p.status == "pending"
            for p in self.payment_repo.get_payments_for_order(order_id)
        )

    # ------------------------------------------------------------------
    # Phase 2 — frontend demo action / webhook
    # ------------------------------------------------------------------

    def _get_owned_payment(self, reference: str, current_user: User) -> Payment:
        txn = self.payment_repo.get_charge_transaction_by_reference(reference)
        if txn is None or txn.payment is None:
            raise NotFoundException("Payment transaction not found")
        order = txn.payment.order
        # Ownership + existence are indistinguishable (IDOR-safe).
        if order is None or order.user_id != current_user.id:
            raise NotFoundException("Payment transaction not found")
        return txn.payment

    def _verify_charge(self, payment: Payment) -> None:
        """Demo security checks before any state change: order, amount, currency."""
        order = payment.order
        if order is None:
            raise NotFoundException("Order not found")
        if payment.status != "pending":
            raise ConflictException(
                f"Payment is in state '{payment.status}' and cannot be completed"
            )
        if Decimal(payment.amount) != Decimal(str(order.total_amount)):
            raise ConflictException("Payment amount does not match the order total")
        if payment.currency != settings.CURRENCY:
            raise ConflictException("Payment currency does not match the store currency")

    def _apply_charge_outcome(self, payment: Payment, outcome: str, changed_by: str) -> None:
        order = payment.order
        txn = payment.transactions[0] if payment.transactions else None
        self.payment_repo.settle_charge(payment, txn, outcome) if txn else setattr(
            payment, "status", outcome
        )
        if outcome == "succeeded":
            order.payment_status = "paid"
            if order.order_status == "pending":
                self.order_repo.add_status_history(
                    order_id=order.id,
                    from_status="pending",
                    to_status="confirmed",
                    changed_by=changed_by,
                    note=f"Payment {payment.status} (demo)",
                )
                self.order_repo.update_order_status(order, "confirmed")

    def complete_payment(
        self,
        reference: str,
        data: PaymentCompleteRequest,
        current_user: User,
    ) -> PaymentResponse:
        payment = self._get_owned_payment(reference, current_user)
        self._verify_charge(payment)

        outcome = {
            "success": "succeeded",
            "failure": "failed",
            "cancel": "cancelled",
        }[data.result]
        # Belt-and-braces: the provider checks its own state machine too.
        MockPaymentProvider.assert_charge_state(payment.status, outcome)

        self._apply_charge_outcome(payment, outcome, changed_by=current_user.id)
        self.payment_repo.db.commit()

        logger.info(
            f"DEMO payment {reference} for order {payment.order.id} "
            f"-> {outcome} by user {current_user.id}"
        )
        return PaymentResponse(
            transaction_id=reference,
            status=outcome,
            provider=self.provider.name,
            order_id=payment.order.id,
            amount=payment.order.total_amount,
            currency=payment.currency,
        )

    def handle_webhook(self, event: WebhookEvent) -> dict:
        """Local/demo webhook only — no provider signature verification. It is
        idempotent: re-delivered events whose target state is already reached
        are acknowledged without further processing."""
        outcome_for = {
            "payment.succeeded": "succeeded",
            "payment.failed": "failed",
            "payment.cancelled": "cancelled",
        }

        if event.event in ("refund.pending", "refund.completed", "refund.failed"):
            return self._handle_refund_event(event)

        txn = self.payment_repo.get_charge_transaction_by_reference(event.transaction_id)
        if txn is None or txn.payment is None:
            raise NotFoundException("Payment transaction not found")
        payment = txn.payment
        target = outcome_for[event.event]

        if event.amount is not None and Decimal(event.amount) != Decimal(str(payment.amount)):
            raise BadRequestException("Webhook amount does not match the payment")

        if payment.status == target:
            # Duplicate event — already processed.
            return {"processed": True, "idempotent": True, "status": payment.status}

        if not self._can_reach_charge_outcome(payment.status, target):
            raise ConflictException(
                f"Payment is in state '{payment.status}' and cannot accept '{event.event}'"
            )

        changed_by = payment.user_id
        self._apply_charge_outcome(payment, target, changed_by=changed_by)
        self.payment_repo.db.commit()
        logger.info(f"DEMO webhook {event.event} applied to payment {payment.id}")
        return {"processed": True, "idempotent": False, "status": payment.status}

    @staticmethod
    def _can_reach_charge_outcome(current: str, target: str) -> bool:
        allowed = {
            "succeeded": {"pending"},
            "failed": {"pending"},
            "cancelled": {"pending"},
        }
        return current in allowed.get(target, set())

    def _handle_refund_event(self, event: WebhookEvent) -> dict:
        refund = self.payment_repo.get_refund_by_provider_reference(event.transaction_id)
        if refund is None:
            raise NotFoundException("Refund transaction not found")
        payment = refund.payment
        order = payment.order

        if event.event == "refund.pending":
            if refund.status == "pending":
                return {"processed": True, "idempotent": True, "status": "pending"}
            if refund.status not in ("requested", "failed"):
                raise ConflictException(f"Refund is in state '{refund.status}'")
            refund.status = "pending"
            payment.status = "refund_pending"
            self.payment_repo.db.commit()
            return {"processed": True, "idempotent": False, "status": "pending"}

        if event.event == "refund.completed":
            if refund.status == "completed":
                return {"processed": True, "idempotent": True, "status": "completed"}
            if refund.status not in ("requested", "pending"):
                raise ConflictException(f"Refund is in state '{refund.status}'")
            self.payment_repo.complete_refund(refund, payment, order)
            self.payment_repo.db.commit()
            return {"processed": True, "idempotent": False, "status": "completed"}

        # refund.failed
        if refund.status == "failed":
            return {"processed": True, "idempotent": True, "status": "failed"}
        if refund.status not in ("requested", "pending"):
            raise ConflictException(f"Refund is in state '{refund.status}'")
        refund.status = "failed"
        # No money moved — the charge remains captured.
        if payment.status == "refund_pending":
            payment.status = "failed"
        self.payment_repo.db.commit()
        return {"processed": True, "idempotent": False, "status": "failed"}