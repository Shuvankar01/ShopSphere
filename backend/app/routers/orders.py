"""Orders router — checkout, listing, detail, admin lifecycle, customer cancel."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from app.schemas.order import (
    CheckoutQuoteRequest,
    CheckoutQuoteResponse,
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
)
from app.services.order_service import OrderService
from app.repositories.address_repo import AddressRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.cart_repo import CartRepository
from app.repositories.coupon_repo import CouponRepository
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.payment_repo import PaymentRepository
from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/orders", tags=["orders"])


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    return OrderService(
        OrderRepository(db),
        CartRepository(db),
        InventoryRepository(db),
        CouponRepository(db),
        PaymentRepository(db),
        AddressRepository(db),
    )


@router.post("/create", response_model=OrderResponse, status_code=201)
def create_order(
    order_in: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    svc: OrderService = Depends(get_order_service),
):
    return svc.create_order(order_in, current_user)


@router.post("/quote", response_model=CheckoutQuoteResponse)
def quote_checkout(
    quote_in: CheckoutQuoteRequest,
    current_user: User = Depends(get_current_active_user),
    svc: OrderService = Depends(get_order_service),
):
    """Authoritative pre-checkout totals for the current cart. Display-only;
    the same math is recomputed when the order is actually created."""
    return svc.quote_checkout(quote_in.shipping_method, current_user)


@router.get("", response_model=List[OrderResponse])
def get_user_orders(
    current_user: User = Depends(get_current_active_user),
    svc: OrderService = Depends(get_order_service),
):
    return svc.get_user_orders(current_user)


@router.get("/{id}", response_model=OrderResponse)
def get_order(
    id: str,
    current_user: User = Depends(get_current_active_user),
    svc: OrderService = Depends(get_order_service),
):
    return svc.get_order(id, current_user)


@router.post("/{id}/cancel", response_model=OrderResponse)
def cancel_order(
    id: str,
    current_user: User = Depends(get_current_active_user),
    svc: OrderService = Depends(get_order_service),
    reason: Optional[str] = None,
):
    """Customers (and admins) can cancel from pre-shipment states; the demo
    payment is auto-refunded if the order was already paid."""
    return svc.cancel_order(id, current_user, reason=reason)


@router.put("/{id}/status", response_model=OrderResponse)
def update_order_status(
    id: str,
    status_update: OrderStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    svc: OrderService = Depends(get_order_service),
):
    return svc.update_order_status(id, status_update, current_user)