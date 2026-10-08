"""Repository for payments / payment transactions / refunds."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.payment import Payment, PaymentTransaction, Refund


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

    def create_charge(
        self,
        order: Order,
        user_id: str,
        payment_method: str,
        amount: Decimal,
    ) -> tuple[Payment, PaymentTransaction]:
        """Record a payment attempt + its charge transaction (no commit)."""
        payment = Payment(
            order_id=order.id,
            user_id=user_id,
            payment_method=payment_method,
            amount=amount,
            status="succeeded",  # demo payments settle immediately
        )
        self.db.add(payment)
        self.db.flush()

        transaction = PaymentTransaction(
            payment_id=payment.id,
            type="charge",
            amount=amount,
            status="succeeded",
            reference=f"txn_{uuid.uuid4().hex[:16]}",
        )
        self.db.add(transaction)
        self.db.flush()
        return payment, transaction

    def create_refund(
        self,
        payment: Payment,
        amount: Decimal,
        reason: str | None = None,
    ) -> Refund:
        refund = Refund(
            payment_id=payment.id,
            order_id=payment.order_id,
            amount=amount,
            status="requested",
            reason=reason,
        )
        self.db.add(refund)
        self.db.flush()
        return refund
