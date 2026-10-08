"""Payment domain: Payment (one per attempt), PaymentTransaction (audit trail
of individual operations) and Refund.

Payments are DEMO-only (no external provider): the server records the attempt
and the outcome; it never trusts a success flag from the client.
`Order.payment_method` keeps recording the method chosen at checkout.
"""
import uuid
from decimal import Decimal
from sqlalchemy import (
    Column, String, ForeignKey, DateTime, Numeric, Text, CheckConstraint, Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base

PAYMENT_STATUSES = ("pending", "succeeded", "failed", "refunded")
REFUND_STATUSES = ("requested", "completed", "failed")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    payment_method = Column(String(50), nullable=False)  # card / paypal / cod / upi / ...
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    order = relationship("Order", back_populates="payments")
    transactions = relationship("PaymentTransaction", back_populates="payment", cascade="all, delete-orphan")
    refunds = relationship("Refund", back_populates="payment", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
        Index("ix_payments_order_status", "order_id", "status"),
    )


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    payment_id = Column(String, ForeignKey("payments.id"), nullable=False, index=True)
    type = Column(String(30), nullable=False, default="charge")  # charge / refund
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False)  # succeeded / failed
    reference = Column(String(100), nullable=False, unique=True)  # provider/demo txn id
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    payment = relationship("Payment", back_populates="transactions")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_txn_amount_positive"),
    )


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    payment_id = Column(String, ForeignKey("payments.id"), nullable=False, index=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="requested")
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    payment = relationship("Payment", back_populates="refunds")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_refund_amount_positive"),
    )
