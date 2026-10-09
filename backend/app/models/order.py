import uuid
from decimal import Decimal
from sqlalchemy import Column, String, ForeignKey, Integer, DateTime, Numeric, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base

class Order(Base):
    """Checkout totals are computed server-side only — subtotal, coupon discount,
    tax, shipping and grand total are snapshotted here at creation time. The
    order also keeps an immutable snapshot of the shipping address so later
    address-book edits can never change a historical order."""

    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Price breakdown (backend-computed Decimals, never trusted from the client).
    subtotal = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    discount_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    tax_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    total_amount = Column(Numeric(10, 2), nullable=False)

    # Controlled order lifecycle (see schemas.order.VALID_TRANSITIONS):
    # pending -> confirmed -> processing -> packed -> shipped ->
    # out_for_delivery -> delivered, with cancellation from pre-shipment states.
    order_status = Column(String(50), default="pending")
    # Kept separate from order state: pending / paid / failed / refunded / partially_refunded
    payment_status = Column(String(50), default="pending")
    # Method chosen at checkout — kept on the order (the actual payment attempts
    # live in payments / payment_transactions).
    payment_method = Column(String(50), nullable=False, default="card")

    # Shipping: chosen demo method, its charge, an immutable address snapshot
    # (JSON string) plus a human-readable copy, and demo tracking data.
    shipping_method = Column(String(50), nullable=False, default="standard")
    shipping_cost = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    shipping_address = Column(String(1000), nullable=False)
    shipping_address_snapshot = Column(Text, nullable=True)
    tracking_number = Column(String(100), nullable=True)
    shipment_status = Column(String(20), nullable=False, default="not_shipped")

    coupon_id = Column(String, ForeignKey("coupons.id"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    status_history = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at",
    )
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    coupon = relationship("Coupon")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")


class OrderStatusHistory(Base):
    """Every order state transition, including the initial 'pending' row."""
    __tablename__ = "order_status_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)  # NULL for the initial entry
    to_status = Column(String(50), nullable=False)
    changed_by = Column(String, ForeignKey("users.id"), nullable=True)
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="status_history")
