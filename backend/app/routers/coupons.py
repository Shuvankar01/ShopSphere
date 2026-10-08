"""Coupons router — admin lifecycle for discount coupons (cart application lives in the cart router)."""
from __future__ import annotations
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.repositories.coupon_repo import CouponRepository
from app.schemas.coupon import CouponCreate, CouponResponse, CouponUpdate
from app.services.coupon_service import CouponService

router = APIRouter(prefix="/coupons", tags=["coupons"])


def get_coupon_service(db: Session = Depends(get_db)) -> CouponService:
    return CouponService(CouponRepository(db))


@router.get("", response_model=List[CouponResponse])
def list_coupons(
    current_user: User = Depends(get_current_active_user),
    svc: CouponService = Depends(get_coupon_service),
):
    return svc.list_coupons(current_user)


@router.post("", response_model=CouponResponse, status_code=201)
def create_coupon(
    data: CouponCreate,
    current_user: User = Depends(get_current_active_user),
    svc: CouponService = Depends(get_coupon_service),
):
    return svc.create_coupon(data, current_user)


@router.put("/{coupon_id}", response_model=CouponResponse)
def update_coupon(
    coupon_id: str,
    data: CouponUpdate,
    current_user: User = Depends(get_current_active_user),
    svc: CouponService = Depends(get_coupon_service),
):
    return svc.update_coupon(coupon_id, data, current_user)


@router.delete("/{coupon_id}", status_code=204)
def deactivate_coupon(
    coupon_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: CouponService = Depends(get_coupon_service),
):
    svc.deactivate_coupon(coupon_id, current_user)