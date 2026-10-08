"""Coupon repository — coupon lookup, lifecycle, and usage recording."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.coupon import Coupon, CouponUsage
from app.schemas.coupon import CouponCreate, CouponUpdate


class CouponRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_code(self, code: str) -> Optional[Coupon]:
        return (
            self.db.query(Coupon)
            .filter(func.upper(Coupon.code) == code.strip().upper())
            .first()
        )

    def get(self, coupon_id: str) -> Optional[Coupon]:
        return self.db.query(Coupon).filter(Coupon.id == coupon_id).first()

    def list_all(self) -> List[Coupon]:
        return self.db.query(Coupon).order_by(Coupon.created_at.desc()).all()

    def create(self, data: CouponCreate) -> Coupon:
        coupon = Coupon(**data.model_dump())
        self.db.add(coupon)
        self.db.commit()
        self.db.refresh(coupon)
        return coupon

    def update(self, coupon: Coupon, data: CouponUpdate) -> Coupon:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(coupon, field, value)
        self.db.commit()
        self.db.refresh(coupon)
        return coupon

    def has_user_used(self, coupon_id: str, user_id: str) -> bool:
        return (
            self.db.query(CouponUsage)
            .filter(
                CouponUsage.coupon_id == coupon_id,
                CouponUsage.user_id == user_id,
            )
            .first()
            is not None
        )

    def record_usage(self, coupon: Coupon, user_id: str, discount_amount: Decimal) -> None:
        """Bind a coupon to a user (cart application). No commit — caller commits."""
        usage = CouponUsage(
            coupon_id=coupon.id,
            user_id=user_id,
            discount_amount=discount_amount,
        )
        coupon.used_count += 1
        self.db.add(usage)

    def is_usable(self, coupon: Coupon, user_id: str, subtotal: Decimal) -> bool:
        """Business-rule gate shared by apply and checkout."""
        if not coupon.is_active:
            return False
        now = datetime.now(timezone.utc)
        if coupon.starts_at is not None and coupon.starts_at > now:
            return False
        if coupon.ends_at is not None and coupon.ends_at < now:
            return False
        if coupon.min_order_amount is not None and subtotal < Decimal(str(coupon.min_order_amount)):
            return False
        if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
            return False
        # A user may only ever use a coupon once.
        if self.has_user_used(coupon.id, user_id):
            return False
        return True

    def discount_for(self, coupon: Coupon, subtotal: Decimal) -> Decimal:
        """Compute the discount amount for a subtotal (never negative)."""
        subtotal = Decimal(str(subtotal))
        if coupon.discount_type == "percent":
            amount = (subtotal * Decimal(str(coupon.discount_value)) / Decimal("100")).quantize(
                Decimal("0.01")
            )
        else:
            amount = min(subtotal, Decimal(str(coupon.discount_value)))
        return max(Decimal("0.00"), amount)