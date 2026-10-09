"""Coupon repository — coupon lookup, lifecycle, restriction-aware eligibility
and race-safe usage recording.

Overuse is prevented at CHECKOUT by locking the coupon row (`SELECT ... FOR
UPDATE`) before re-validating and incrementing used_count, so two concurrent
checkouts cannot both consume the last allowed use.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException
from app.models.coupon import Coupon, CouponUsage
from app.schemas.coupon import CouponCreate, CouponUpdate


def _parse_id_list(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(v) for v in value]
    except (ValueError, TypeError):
        pass
    return []


@dataclass
class CouponLine:
    """A cart line projected for restriction checks: a coupon restricted to
    products/categories only applies to matching lines."""

    id: str
    category_id: Optional[str]
    price: Decimal
    discount_price: Optional[Decimal]
    quantity: int
    is_active: bool = True


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
        self._serialize_restrictions(coupon)
        self.db.add(coupon)
        self.db.commit()
        self.db.refresh(coupon)
        return coupon

    def update(self, coupon: Coupon, data: CouponUpdate) -> Coupon:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(coupon, field, value)
        self._serialize_restrictions(coupon)
        self.db.commit()
        self.db.refresh(coupon)
        return coupon

    # ------------------------------------------------------------------
    # Eligibility
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_restrictions(coupon: Coupon) -> None:
        """Persist restriction id lists as JSON text columns."""
        if coupon.applies_to_product_ids is not None and not isinstance(
            coupon.applies_to_product_ids, str
        ):
            coupon.applies_to_product_ids = json.dumps(list(coupon.applies_to_product_ids))
        if coupon.applies_to_category_ids is not None and not isinstance(
            coupon.applies_to_category_ids, str
        ):
            coupon.applies_to_category_ids = json.dumps(list(coupon.applies_to_category_ids))

    def applicable_product_ids(self, coupon: Coupon) -> List[str]:
        return _parse_id_list(coupon.applies_to_product_ids)

    def applicable_category_ids(self, coupon: Coupon) -> List[str]:
        return _parse_id_list(coupon.applies_to_category_ids)

    def has_restrictions(self, coupon: Coupon) -> bool:
        return bool(
            self.applicable_product_ids(coupon) or self.applicable_category_ids(coupon)
        )

    def count_user_usages(self, coupon_id: str, user_id: str) -> int:
        return (
            self.db.query(func.count(CouponUsage.id))
            .filter(
                CouponUsage.coupon_id == coupon_id,
                CouponUsage.user_id == user_id,
            )
            .scalar()
            or 0
        )

    def eligible_subtotal(
        self, coupon: Coupon, subtotal: Decimal, items: Optional[List] = None
    ) -> Decimal:
        """Subtotal of the cart lines the coupon may be applied to. `items` is a
        list of CouponLine objects."""
        if not self.has_restrictions(coupon):
            return Decimal(str(subtotal))
        product_ids = set(self.applicable_product_ids(coupon))
        category_ids = set(self.applicable_category_ids(coupon))
        eligible = Decimal("0.00")
        for line in items or []:
            if not line.is_active:
                continue
            if line.id in product_ids or line.category_id in category_ids:
                price = line.discount_price if line.discount_price is not None else line.price
                eligible += Decimal(str(price)) * line.quantity
        return eligible

    def is_usable(
        self,
        coupon: Coupon,
        user_id: str,
        subtotal: Decimal,
        items: Optional[List] = None,
    ) -> bool:
        """Business-rule gate shared by apply and checkout (read-only precheck —
        membership/limits are authoritatively enforced under lock at checkout)."""
        if not coupon.is_active:
            return False
        now = datetime.now(timezone.utc)
        if coupon.starts_at is not None and coupon.starts_at > now:
            return False
        if coupon.ends_at is not None and coupon.ends_at < now:
            return False
        if coupon.min_order_amount is not None and subtotal < Decimal(
            str(coupon.min_order_amount)
        ):
            return False
        if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
            return False
        # Per-user usage limit.
        if self.count_user_usages(coupon.id, user_id) >= (coupon.per_user_limit or 1):
            return False
        # Product/category restrictions: at least one qualifying line required.
        if self.has_restrictions(coupon):
            if self.eligible_subtotal(coupon, subtotal, items) <= 0:
                return False
        return True

    def discount_for(
        self,
        coupon: Coupon,
        subtotal: Decimal,
        items: Optional[List] = None,
    ) -> Decimal:
        """Compute the discount (never negative, never above the eligible base)."""
        base = self.eligible_subtotal(coupon, subtotal, items)
        if base <= 0:
            return Decimal("0.00")
        if coupon.discount_type == "percent":
            amount = (base * Decimal(str(coupon.discount_value)) / Decimal("100")).quantize(
                Decimal("0.01")
            )
            cap = Decimal(str(coupon.max_discount_amount)) if coupon.max_discount_amount is not None else base
            amount = min(amount, cap)
        else:
            amount = min(base, Decimal(str(coupon.discount_value)))
        amount = min(base, amount)
        return max(Decimal("0.00"), amount)

    def record_usage(
        self,
        coupon: Coupon,
        user_id: str,
        discount_amount: Decimal,
        subtotal: Optional[Decimal] = None,
        items: Optional[List] = None,
        order_id: Optional[str] = None,
    ) -> None:
        """Consume one use. Runs under a row lock so two concurrent checkouts
        cannot both pass the limit checks. No commit — the caller owns the
        transaction (atomic checkout)."""
        locked = (
            self.db.query(Coupon)
            .filter(Coupon.id == coupon.id)
            .with_for_update()
            .first()
        )
        if locked is None:
            raise BadRequestException("Coupon no longer exists")
        if not self.is_usable(locked, user_id, subtotal or Decimal("0.00"), items):
            raise BadRequestException("Coupon is no longer applicable or has run out of uses")
        usage = CouponUsage(
            coupon_id=locked.id,
            user_id=user_id,
            order_id=order_id,
            discount_amount=discount_amount,
        )
        locked.used_count += 1
        self.db.add(usage)