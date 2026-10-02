from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.schemas.admin import AdminStatsResponse
from app.schemas.user import UserResponse
from app.schemas.order import OrderResponse
from app.schemas.product import ProductResponse
from app.services.admin_service import AdminService
from app.repositories.user_repo import UserRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.order_repo import OrderRepository
from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])

def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    return AdminService(
        user_repo=UserRepository(db),
        product_repo=ProductRepository(db),
        order_repo=OrderRepository(db)
    )

@router.get("/dashboard", response_model=AdminStatsResponse)
def get_dashboard(
    current_user: User = Depends(get_current_active_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    return admin_service.get_dashboard_stats(current_user)

@router.get("/users", response_model=List[UserResponse])
def get_users(
    current_user: User = Depends(get_current_active_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    return admin_service.get_all_users(current_user)

@router.get("/orders", response_model=List[OrderResponse])
def get_orders(
    current_user: User = Depends(get_current_active_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    return admin_service.get_all_orders(current_user)

@router.get("/products", response_model=List[ProductResponse])
def get_products(
    current_user: User = Depends(get_current_active_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    return admin_service.get_all_products(current_user)
