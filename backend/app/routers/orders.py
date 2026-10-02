from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from app.services.order_service import OrderService
from app.repositories.order_repo import OrderRepository
from app.repositories.cart_repo import CartRepository
from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/orders", tags=["orders"])

def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    return OrderService(OrderRepository(db), CartRepository(db))

@router.post("/create", response_model=OrderResponse)
def create_order(
    order_in: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    order_service: OrderService = Depends(get_order_service)
):
    return order_service.create_order(order_in, current_user)

@router.get("", response_model=List[OrderResponse])
def get_user_orders(
    current_user: User = Depends(get_current_active_user),
    order_service: OrderService = Depends(get_order_service)
):
    return order_service.get_user_orders(current_user)

@router.get("/{id}", response_model=OrderResponse)
def get_order(
    id: str,
    current_user: User = Depends(get_current_active_user),
    order_service: OrderService = Depends(get_order_service)
):
    return order_service.get_order(id, current_user)

@router.put("/{id}/status", response_model=OrderResponse)
def update_order_status(
    id: str,
    status_update: OrderStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    order_service: OrderService = Depends(get_order_service)
):
    return order_service.update_order_status(id, status_update, current_user)
