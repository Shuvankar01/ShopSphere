"""Coupon Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class CouponCreate(BaseModel):
    code: str
    discount_type: str = "percent"  # percent / fixed
    discount_value: Decimal
    min_order_amount: Optional[Decimal] = None
    max_uses: Optional[int] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        code = v.strip().upper()
        if not code:
            raise ValueError("Code cannot be empty")
        if len(code) > 50:
            raise ValueError("Code too long")
        return code

    @field_validator("discount_type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        if v not in ("percent", "fixed"):
            raise ValueError("discount_type must be 'percent' or 'fixed'")
        return v

    @field_validator("discount_value")
    @classmethod
    def value_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Discount value must be positive")
        return v

    @field_validator("discount_value")
    @classmethod
    def percent_bounds(cls, v: Decimal, info) -> Decimal:
        if info.data.get("discount_type") == "percent" and v > 100:
            raise ValueError("Percent discount cannot exceed 100")
        return v


class CouponUpdate(BaseModel):
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    min_order_amount: Optional[Decimal] = None
    max_uses: Optional[int] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class CouponResponse(BaseModel):
    id: str
    code: str
    discount_type: str
    discount_value: Decimal
    min_order_amount: Optional[Decimal] = None
    max_uses: Optional[int] = None
    used_count: int
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CouponApply(BaseModel):
    code: str
