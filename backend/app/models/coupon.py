"""Coupon domain: Coupons and their usage records (foundation for promotions)."""
import uuid
from decimal import Decimal
from sqlalchemy import (
    Column, String, Integer, ForeignKey, DateTime, Numeric, Boolean,
    CheckConstraint, UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    discount_type = Column(String(20), nullable=False, default="percent")  # percent / fixed
    discount_value = Column(Numeric(10, 2), nullable=False)
    min_order_amount = Column(Numeric(10, 2), nullable=True)
    max_uses = Column(Integer, nullable=True)  # NULL = unlimited
    used_count = Column(Integer, nullable=False, default=0)
    starts_at = Column(DateTime(timezone=True), nullable=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    usages = relationship("CouponUsage", back_populates="coupon", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("discount_value > 0", name="ck_coupon_value_positive"),
        CheckConstraint(
            "discount_type IN ('percent', 'fixed')",
            name="ck_coupon_discount_type",
        ),
        CheckConstraint(
            "discount_type <> 'percent' OR discount_value <= 100",
            name="ck_coupon_percent_lte_100",
        ),
    )


class CouponUsage(Base):
    __tablename__ = "coupon_usages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    coupon_id = Column(String, ForeignKey("coupons.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    # Nullable: recorded when a coupon is applied; bound to an order on checkout.
    order_id = Column(String, ForeignKey("orders.id"), nullable=True, index=True)
    discount_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    coupon = relationship("Coupon", back_populates="usages")

    __table_args__ = (
        # one use per customer per coupon (simple, enforceable rule)
        UniqueConstraint("coupon_id", "user_id", name="uq_coupon_usage_per_user"),
        CheckConstraint("discount_amount > 0", name="ck_coupon_usage_amount_positive"),
    )
