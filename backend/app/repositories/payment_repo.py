"""Repository for payments / payment transactions / refunds (DEMO provider)."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.payment import Payment, PaymentTransaction, Refund

DEMO_PROVIDER = "DEMO"


def demo_reference(prefix: str = "txn") -> str:
    """Unique DEMO provider reference — the thing the frontend/webhook quote."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_payment(self, payment_id: str) -> Payment | None:
        return self.db.query(Payment).filter(Payment.id == payment_id).first()

    def get_payments_for_order(self, order_id: str) -> list[Payment]:
        return (
            self.db.query(Payment)
            .filter(Payment.order_id == order_id)
            .order_by(Payment.created_at.desc())
            .all()
        )

    def get_charge_transaction_by_reference(self, reference: str) -> Optional[PaymentTransaction]:
        return (
            self.db.query(PaymentTransaction)
            .filter(PaymentTransaction.reference == reference)
            .first()
        )

    def create_payment(
        self,
        order: Order,
        user_id: str,
        payment_method: str,
        amount: Decimal,
        currency: str,
    ) -> Tuple[Payment, PaymentTransaction]:
        """Record a DEMO payment attempt (pending) + its charge transaction.
        No commit — the caller settles the transaction."""
        payment = Payment(
            order_id=order.id,
            user_id=user_id,
            payment_method=payment_method,
            amount=amount,
            currency=currency,
            status="pending",
        )
        self.db.add(payment)
        self.db.flush()

        transaction = PaymentTransaction(
            payment_id=payment.id,
            type="charge",
            amount=amount,
            status="pending",
            provider=DEMO_PROVIDER,
            reference=demo_reference("demo"),
        )
        self.db.add(transaction)
        self.db.flush()
        return payment, transaction

    def settle_charge(self, payment: Payment, transaction: PaymentTransaction, status: str) -> None:
        """Flip a pending charge to its terminal demo outcome (succeeded/failed/cancelled)."""
        payment.status = status
        transaction.status = status

    # ------------------------------------------------------------------
    # Refunds
    # ------------------------------------------------------------------

    def create_refund(
        self,
        payment: Payment,
        amount: Decimal,
        reason: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Refund:
        refund = Refund(
            payment_id=payment.id,
            order_id=payment.order_id,
            amount=amount,
            status="requested",
            reason=reason,
            idempotency_key=idempotency_key,
            provider_reference=demo_reference("refund"),
        )
        self.db.add(refund)
        self.db.flush()
        # While a refund is being processed the payment is refund_pending.
        payment.status = "refund_pending"
        return refund

    def complete_refund(self, refund: Refund, payment: Payment, order: Order) -> None:
        """Demo provider completes the refund: record the refund transaction and
        move payment + order to their (partially) refunded states."""
        txn = PaymentTransaction(
            payment_id=payment.id,
            type="refund",
            amount=refund.amount,
            status="succeeded",
            provider=DEMO_PROVIDER,
            reference=refund.provider_reference or demo_reference("refund"),
        )
        self.db.add(txn)
        refund.status = "completed"
        # autoflush is disabled — flush so refunded_total() sees this refund.
        self.db.flush()
        total_refunded = self.refunded_total(payment)
        if total_refunded >= payment.amount:
            payment.status = "refunded"
            order.payment_status = "refunded"
        else:
            payment.status = "partially_refunded"
            order.payment_status = "partially_refunded"

    def refunded_total(self, payment: Payment) -> Decimal:
        from sqlalchemy import func
        total = (
            self.db.query(func.coalesce(func.sum(Refund.amount), 0))
            .filter(Refund.payment_id == payment.id, Refund.status == "completed")
            .scalar()
        )
        return Decimal(str(total))

    def get_refund(self, refund_id: str) -> Refund | None:
        return self.db.query(Refund).filter(Refund.id == refund_id).first()

    def get_refund_by_idempotency_key(self, key: str) -> Refund | None:
        return self.db.query(Refund).filter(Refund.idempotency_key == key).first()

    def get_refund_by_provider_reference(self, reference: str) -> Refund | None:
        return self.db.query(Refund).filter(Refund.provider_reference == reference).first()

    def get_refunds_for_order(self, order_id: str) -> List[Refund]:
        return (
            self.db.query(Refund)
            .filter(Refund.order_id == order_id)
            .order_by(Refund.created_at.desc())
            .all()
        )

    def get_all_refunds(self) -> List[Refund]:
        return self.db.query(Refund).order_by(Refund.created_at.desc()).all()