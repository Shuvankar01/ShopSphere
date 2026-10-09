"""Coupon Pydantic schemas — percent/fixed, caps, windows, limits, restrictions."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class CouponCreate(BaseModel):
    code: str
    discount_type: str = "percent"  # percent / fixed
    discount_value: Decimal
    min_order_amount: Optional[Decimal] = None
    max_discount_amount: Optional[Decimal] = None
    max_uses: Optional[int] = None
    per_user_limit: int = 1
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: bool = True
    # Restriction lists: when non-empty, the coupon only applies to lines in the
    # matching products/categories.
    applies_to_product_ids: List[str] = []
    applies_to_category_ids: List[str] = []

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

    @field_validator("per_user_limit")
    @classmethod
    def limit_positive(cls, v: int) -> int:
        if v is not None and v <= 0:
            raise ValueError("per_user_limit must be positive")
        return v

    @model_validator(mode="after")
    def percent_cap_positive(self):
        if (
            self.max_discount_amount is not None
            and self.max_discount_amount <= 0
        ):
            raise ValueError("max_discount_amount must be positive")
        return self


class CouponUpdate(BaseModel):
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    min_order_amount: Optional[Decimal] = None
    max_discount_amount: Optional[Decimal] = None
    max_uses: Optional[int] = None
    per_user_limit: Optional[int] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    applies_to_product_ids: Optional[List[str]] = None
    applies_to_category_ids: Optional[List[str]] = None


class CouponResponse(BaseModel):
    id: str
    code: str
    discount_type: str
    discount_value: Decimal
    min_order_amount: Optional[Decimal] = None
    max_discount_amount: Optional[Decimal] = None
    max_uses: Optional[int] = None
    used_count: int
    per_user_limit: int = 1
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: bool
    applies_to_product_ids: List[str] = []
    applies_to_category_ids: List[str] = []
    created_at: datetime

    @field_validator("applies_to_product_ids", "applies_to_category_ids", mode="before")
    @classmethod
    def parse_json_ids(cls, v):
        if isinstance(v, str):
            import json as _json
            try:
                return _json.loads(v)
            except (ValueError, TypeError):
                return []
        return v or []

    model_config = ConfigDict(from_attributes=True)


class CouponApply(BaseModel):
    code: str