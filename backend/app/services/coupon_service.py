"""Coupon service — admin lifecycle for discount coupons."""
from __future__ import annotations

from typing import List

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.models.user import User
from app.repositories.coupon_repo import CouponRepository
from app.schemas.coupon import CouponCreate, CouponResponse, CouponUpdate


class CouponService:
    def __init__(self, coupon_repo: CouponRepository):
        self.coupon_repo = coupon_repo

    def _require_admin(self, user: User) -> None:
        if user.role != "admin":
            raise ForbiddenException("Only admins can manage coupons")

    def list_coupons(self, current_user: User) -> List[CouponResponse]:
        self._require_admin(current_user)
        return [CouponResponse.model_validate(c) for c in self.coupon_repo.list_all()]

    def create_coupon(self, data: CouponCreate, current_user: User) -> CouponResponse:
        self._require_admin(current_user)
        if self.coupon_repo.get_by_code(data.code):
            raise ConflictException(f"Coupon code '{data.code}' already exists")
        return CouponResponse.model_validate(self.coupon_repo.create(data))

    def update_coupon(self, coupon_id: str, data: CouponUpdate, current_user: User) -> CouponResponse:
        self._require_admin(current_user)
        coupon = self.coupon_repo.get(coupon_id)
        if not coupon:
            raise NotFoundException("Coupon not found")
        return CouponResponse.model_validate(self.coupon_repo.update(coupon, data))

    def deactivate_coupon(self, coupon_id: str, current_user: User) -> None:
        """Soft deactivation — historical usage rows must survive."""
        self._require_admin(current_user)
        coupon = self.coupon_repo.get(coupon_id)
        if not coupon:
            raise NotFoundException("Coupon not found")
        coupon.is_active = False
        self.coupon_repo.db.commit()
