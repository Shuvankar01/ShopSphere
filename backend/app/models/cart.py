"""Cart models updated with Decimal pricing and coupon support."""
import uuid
from decimal import Decimal

from sqlalchemy import (
    Column,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Cart(Base):
    __tablename__ = "carts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    subtotal = Column(Numeric(10, 2), nullable=False, default=0)
    coupon_id = Column(String, ForeignKey("coupons.id"), nullable=True, index=True)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")
    coupon = relationship("Coupon")

    __table_args__ = (
        # One cart per user. Name matches the constraint in the databases
        # created by migrations (PG auto-naming), so alembic sees no diff.
        UniqueConstraint("user_id", name="carts_user_id_key"),
        CheckConstraint("discount_amount >= 0", name="ck_cart_discount_nonneg"),
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    cart_id = Column(String, ForeignKey("carts.id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)   # price snapshotted at add-time
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")
