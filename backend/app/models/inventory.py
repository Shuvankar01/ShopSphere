"""Inventory models: Inventory (per-product stock) and InventoryMovement (history log)."""
import uuid
from sqlalchemy import (
    Column, String, Integer, ForeignKey, Text, DateTime, Numeric,
    CheckConstraint, Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Inventory(Base):
    """
    One row per product — single source of truth for stock levels.

    physical_stock  : total units physically in stock
    reserved_stock  : units reserved by pending orders (not yet shipped)
    available_stock : computed as physical_stock - reserved_stock (virtual, not a real column)
    """
    __tablename__ = "inventory"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String, ForeignKey("products.id"), nullable=False, unique=True, index=True)
    physical_stock = Column(Integer, nullable=False, default=0)
    reserved_stock = Column(Integer, nullable=False, default=0)
    low_stock_threshold = Column(Integer, nullable=False, default=5)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="inventory")
    movements = relationship("InventoryMovement", back_populates="inventory", cascade="all, delete-orphan")

    @property
    def available_stock(self) -> int:
        return max(0, self.physical_stock - self.reserved_stock)

    @property
    def is_low_stock(self) -> bool:
        return self.available_stock <= self.low_stock_threshold

    __table_args__ = (
        CheckConstraint("physical_stock >= 0", name="ck_inventory_physical_nonneg"),
        CheckConstraint("reserved_stock >= 0", name="ck_inventory_reserved_nonneg"),
        CheckConstraint("reserved_stock <= physical_stock", name="ck_inventory_reserved_le_physical"),
    )


class InventoryMovement(Base):
    """
    Immutable audit log of every stock change.
    movement_type: 'add', 'remove', 'reserve', 'release', 'deduct', 'adjust'
    """
    __tablename__ = "inventory_movements"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    inventory_id = Column(String, ForeignKey("inventory.id"), nullable=False, index=True)
    movement_type = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)           # positive = added, negative = removed
    reference_id = Column(String, nullable=True)        # order_id, adjustment_id, etc.
    reference_type = Column(String(50), nullable=True)  # 'order', 'admin_adjustment', etc.
    note = Column(Text, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    inventory = relationship("Inventory", back_populates="movements")

    __table_args__ = (
        Index("ix_inv_movements_inventory_id", "inventory_id"),
        Index("ix_inv_movements_created_at", "created_at"),
    )
