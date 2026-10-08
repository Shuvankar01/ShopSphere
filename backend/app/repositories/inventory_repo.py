"""Inventory repository with atomic stock operations and concurrency protection."""
from __future__ import annotations
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import Inventory, InventoryMovement


class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_product(self, product_id: str, for_update: bool = False) -> Optional[Inventory]:
        """Get inventory row; use for_update=True to acquire a row-level lock."""
        stmt = select(Inventory).where(Inventory.product_id == product_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.execute(stmt).scalar_one_or_none()

    def create_for_product(self, product_id: str, initial_stock: int = 0) -> Inventory:
        inv = Inventory(product_id=product_id, physical_stock=initial_stock)
        self.db.add(inv)
        self.db.flush()
        self._log(inv, "add", initial_stock, note="Initial stock")
        self.db.commit()
        self.db.refresh(inv)
        return inv

    def set_stock(
        self,
        inventory: Inventory,
        physical_stock: int,
        low_stock_threshold: Optional[int] = None,
        actor_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Inventory:
        """Seller / admin sets physical stock directly."""
        diff = physical_stock - inventory.physical_stock
        inventory.physical_stock = physical_stock
        if low_stock_threshold is not None:
            inventory.low_stock_threshold = low_stock_threshold
        self.db.flush()
        movement_type = "add" if diff >= 0 else "remove"
        self._log(inventory, movement_type, diff, created_by=actor_id, note=note)
        self.db.commit()
        self.db.refresh(inventory)
        return inventory

    def adjust_stock(
        self,
        inventory: Inventory,
        quantity: int,
        actor_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Inventory:
        """Admin delta adjustment (positive = add, negative = remove)."""
        inventory.physical_stock += quantity
        if inventory.physical_stock < 0:
            raise ValueError("Adjustment would result in negative physical stock")
        self.db.flush()
        movement_type = "add" if quantity >= 0 else "remove"
        self._log(inventory, "adjust", quantity, created_by=actor_id, note=note)
        self.db.commit()
        self.db.refresh(inventory)
        return inventory

    def reserve(
        self,
        inventory: Inventory,
        quantity: int,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
    ) -> Inventory:
        """Reserve stock when an order is placed. Raises ValueError if insufficient."""
        if inventory.available_stock < quantity:
            raise ValueError(
                f"Insufficient stock: available={inventory.available_stock}, requested={quantity}"
            )
        inventory.reserved_stock += quantity
        self.db.flush()
        self._log(inventory, "reserve", quantity, reference_id=reference_id, reference_type=reference_type)
        # Do NOT commit here — caller controls the transaction
        return inventory

    def release(
        self,
        inventory: Inventory,
        quantity: int,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
    ) -> Inventory:
        """Release reserved stock back (e.g. order cancelled before fulfilment)."""
        inventory.reserved_stock = max(0, inventory.reserved_stock - quantity)
        self.db.flush()
        self._log(inventory, "release", -quantity, reference_id=reference_id, reference_type=reference_type)
        return inventory

    def deduct(
        self,
        inventory: Inventory,
        quantity: int,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
    ) -> Inventory:
        """Convert reserved → fulfilled: remove from both physical and reserved."""
        inventory.reserved_stock = max(0, inventory.reserved_stock - quantity)
        inventory.physical_stock -= quantity
        if inventory.physical_stock < 0:
            raise ValueError("Deduction would result in negative physical stock")
        self.db.flush()
        self._log(inventory, "deduct", -quantity, reference_id=reference_id, reference_type=reference_type)
        return inventory

    def get_movements(self, inventory_id: str, limit: int = 50) -> List[InventoryMovement]:
        return (
            self.db.query(InventoryMovement)
            .filter(InventoryMovement.inventory_id == inventory_id)
            .order_by(InventoryMovement.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_mine(
        self, seller_id: Optional[str] = None, search: Optional[str] = None, limit: int = 200
    ) -> List[Inventory]:
        """All inventory rows for one seller's catalog (or the whole catalog for admins)."""
        from app.models.product import Product

        query = (
            self.db.query(Inventory)
            .join(Product, Inventory.product_id == Product.id)
        )
        if seller_id is not None:
            query = query.filter(Product.seller_id == seller_id)
        if search:
            query = query.filter(Product.name.ilike(f"%{search}%"))
        return query.order_by(Product.name).limit(limit).all()

    def get_low_stock(self, seller_id: Optional[str] = None, limit: int = 100) -> List[Inventory]:
        """Inventory rows at/below their low-stock threshold (seller-scoped or all)."""
        from app.models.product import Product

        query = (
            self.db.query(Inventory)
            .join(Product, Inventory.product_id == Product.id)
            .filter(
                (Inventory.physical_stock - Inventory.reserved_stock)
                <= Inventory.low_stock_threshold,
            )
        )
        if seller_id is not None:
            query = query.filter(Product.seller_id == seller_id)
        return (
            query.order_by((Inventory.physical_stock - Inventory.reserved_stock).asc())
            .limit(limit)
            .all()
        )

    def _log(
        self,
        inventory: Inventory,
        movement_type: str,
        quantity: int,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        note: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> None:
        movement = InventoryMovement(
            inventory_id=inventory.id,
            movement_type=movement_type,
            quantity=quantity,
            reference_id=reference_id,
            reference_type=reference_type,
            note=note,
            created_by=created_by,
        )
        self.db.add(movement)
