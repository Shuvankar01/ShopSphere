"""Inventory service — business logic for stock management."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.models.inventory import Inventory
from app.models.user import User
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.inventory import (
    InventoryAdjust,
    InventoryMovementResponse,
    InventoryResponse,
    InventoryUpdate,
    LowStockItem,
)


class InventoryService:
    def __init__(self, inventory_repo: InventoryRepository, product_repo: ProductRepository):
        self.inventory_repo = inventory_repo
        self.product_repo = product_repo

    def _get_product_and_check_seller(self, product_id: str, current_user: User):
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        # Inventory is staff-only: customers must never manage (or snoop on)
        # stock levels through this service.
        if current_user.role not in ("seller", "admin"):
            raise ForbiddenException("Seller or admin access required")
        if current_user.role == "seller" and product.seller_id != current_user.id:
            raise ForbiddenException("Not authorized to manage this product's inventory")
        return product

    def _get_inventory_or_create(self, product) -> Inventory:
        """Fetch the inventory row, lazily creating it for products created
        outside the API (seed scripts, legacy rows)."""
        inv = self.inventory_repo.get_by_product(product.id)
        if inv is None:
            try:
                inv = self.inventory_repo.create_for_product(
                    product.id, initial_stock=product.stock
                )
            except IntegrityError:
                # Concurrent request created it first.
                self.inventory_repo.db.rollback()
                inv = self.inventory_repo.get_by_product(product.id)
        return inv

    def get_inventory(self, product_id: str, current_user: User) -> InventoryResponse:
        product = self._get_product_and_check_seller(product_id, current_user)
        inv = self._get_inventory_or_create(product)
        if not inv:
            raise NotFoundException("Inventory record not found")
        return InventoryResponse.model_validate(inv)

    def set_stock(self, product_id: str, data: InventoryUpdate, current_user: User) -> InventoryResponse:
        """Seller or admin sets/replaces physical stock."""
        product = self._get_product_and_check_seller(product_id, current_user)
        inv = self._get_inventory_or_create(product)
        if not inv:
            raise NotFoundException("Inventory record not found")
        if data.physical_stock < inv.reserved_stock:
            raise BadRequestException(
                f"Cannot set stock to {data.physical_stock}: "
                f"{inv.reserved_stock} units are reserved"
            )
        updated = self.inventory_repo.set_stock(
            inv,
            physical_stock=data.physical_stock,
            low_stock_threshold=data.low_stock_threshold,
            actor_id=current_user.id,
            note="Stock update via seller/admin",
        )
        return InventoryResponse.model_validate(updated)

    def adjust_stock(self, product_id: str, data: InventoryAdjust, current_user: User) -> InventoryResponse:
        """Admin-only delta adjustment."""
        if current_user.role != "admin":
            raise ForbiddenException("Only admins can perform delta adjustments")
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        inv = self._get_inventory_or_create(product)
        if not inv:
            raise NotFoundException("Inventory record not found")
        try:
            updated = self.inventory_repo.adjust_stock(
                inv, quantity=data.quantity, actor_id=current_user.id, note=data.note
            )
        except ValueError as e:
            self.inventory_repo.db.rollback()
            raise BadRequestException(str(e)) from None
        return InventoryResponse.model_validate(updated)

    def get_movements(self, product_id: str, current_user: User) -> List[InventoryMovementResponse]:
        product = self._get_product_and_check_seller(product_id, current_user)
        inv = self._get_inventory_or_create(product)
        if not inv:
            raise NotFoundException("Inventory record not found")
        movements = self.inventory_repo.get_movements(inv.id)
        return [InventoryMovementResponse.model_validate(m) for m in movements]

    def get_low_stock(self, current_user: User, limit: int = 100) -> List[LowStockItem]:
        if current_user.role not in ("seller", "admin"):
            raise ForbiddenException("Seller or admin access required")
        seller_id = current_user.id if current_user.role == "seller" else None
        rows = self.inventory_repo.get_low_stock(seller_id=seller_id, limit=limit)
        return [
            LowStockItem(
                product_id=inv.product_id,
                product_name=inv.product.name,
                inventory=InventoryResponse(
                    id=inv.id,
                    product_id=inv.product_id,
                    physical_stock=inv.physical_stock,
                    reserved_stock=inv.reserved_stock,
                    available_stock=inv.available_stock,
                    low_stock_threshold=inv.low_stock_threshold,
                    is_low_stock=inv.is_low_stock,
                    updated_at=inv.updated_at,
                ),
            )
            for inv in rows
        ]

    def get_mine(self, current_user: User, search: Optional[str] = None) -> List[LowStockItem]:
        """Seller dashboard: inventory for every product in the caller's catalog."""
        if current_user.role not in ("seller", "admin"):
            raise ForbiddenException("Seller or admin access required")
        seller_id = current_user.id if current_user.role == "seller" else None
        return self._to_items(self.inventory_repo.get_mine(seller_id, search=search))

    def _to_items(self, rows) -> List[LowStockItem]:
        return [
            LowStockItem(
                product_id=inv.product_id,
                product_name=inv.product.name,
                inventory=InventoryResponse(
                    id=inv.id,
                    product_id=inv.product_id,
                    physical_stock=inv.physical_stock,
                    reserved_stock=inv.reserved_stock,
                    available_stock=inv.available_stock,
                    low_stock_threshold=inv.low_stock_threshold,
                    is_low_stock=inv.is_low_stock,
                    updated_at=inv.updated_at,
                ),
            )
            for inv in rows
        ]
