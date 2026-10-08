"""Inventory Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class InventoryResponse(BaseModel):
    id: str
    product_id: str
    physical_stock: int
    reserved_stock: int
    available_stock: int
    low_stock_threshold: int
    is_low_stock: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryAdjust(BaseModel):
    """Admin-only adjustment."""
    quantity: int    # positive to add, negative to remove
    note: Optional[str] = None


class InventoryUpdate(BaseModel):
    """Seller stock set (replaces physical_stock)."""
    physical_stock: int
    low_stock_threshold: Optional[int] = None

    @field_validator("physical_stock")
    @classmethod
    def nonneg(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Physical stock cannot be negative")
        return v


class InventoryMovementResponse(BaseModel):
    id: str
    inventory_id: str
    movement_type: str
    quantity: int
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LowStockItem(BaseModel):
    product_id: str
    product_name: str
    inventory: InventoryResponse

    model_config = ConfigDict(from_attributes=True)
