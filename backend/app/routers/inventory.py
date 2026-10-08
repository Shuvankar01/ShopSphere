"""Inventory router."""
from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.schemas.inventory import (
    InventoryResponse,
    InventoryAdjust,
    InventoryUpdate,
    InventoryMovementResponse,
    LowStockItem,
)
from app.services.inventory_service import InventoryService
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.product_repo import ProductRepository
from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/inventory", tags=["inventory"])


def get_inventory_service(db: Session = Depends(get_db)) -> InventoryService:
    return InventoryService(InventoryRepository(db), ProductRepository(db))


@router.get("/products/{product_id}", response_model=InventoryResponse)
def get_inventory(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: InventoryService = Depends(get_inventory_service),
):
    return svc.get_inventory(product_id, current_user)


@router.put("/products/{product_id}", response_model=InventoryResponse)
def set_stock(
    product_id: str,
    data: InventoryUpdate,
    current_user: User = Depends(get_current_active_user),
    svc: InventoryService = Depends(get_inventory_service),
):
    """Seller/admin: replace physical stock level."""
    return svc.set_stock(product_id, data, current_user)


@router.post("/products/{product_id}/adjust", response_model=InventoryResponse)
def adjust_stock(
    product_id: str,
    data: InventoryAdjust,
    current_user: User = Depends(get_current_active_user),
    svc: InventoryService = Depends(get_inventory_service),
):
    """Admin-only: delta adjustment."""
    return svc.adjust_stock(product_id, data, current_user)


@router.get("/products/{product_id}/movements", response_model=List[InventoryMovementResponse])
def get_movements(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: InventoryService = Depends(get_inventory_service),
):
    return svc.get_movements(product_id, current_user)


@router.get("/low-stock", response_model=List[LowStockItem])
def get_low_stock(
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    svc: InventoryService = Depends(get_inventory_service),
):
    """Seller: low-stock rows for their own catalog. Admin: for the whole catalog."""
    return svc.get_low_stock(current_user, limit=limit)


@router.get("/mine", response_model=List[LowStockItem])
def get_my_inventory(
    q: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    svc: InventoryService = Depends(get_inventory_service),
):
    """Seller dashboard: inventory rows for the caller's own products."""
    return svc.get_mine(current_user, search=q)
