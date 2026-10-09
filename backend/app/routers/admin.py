from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.admin import AdminStatsResponse
from app.schemas.user import UserResponse
from app.schemas.order import OrderResponse
from app.schemas.product import ProductResponse, ReviewModerationUpdate, ReviewResponse
from app.schemas.return_request import ReturnActionRequest, ReturnResponse
from app.services.admin_service import AdminService
from app.services.return_service import ReturnService
from app.services.refund_service import RefundService
from app.services.product_service import ProductService
from app.repositories.user_repo import UserRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.return_repo import ReturnRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.inventory_repo import InventoryRepository
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


def get_return_service(db: Session = Depends(get_db)) -> ReturnService:
    return ReturnService(
        return_repo=ReturnRepository(db),
        order_repo=OrderRepository(db),
        payment_repo=PaymentRepository(db),
        refund_service=RefundService(OrderRepository(db), PaymentRepository(db)),
    )


def get_moderation_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(
        ProductRepository(db),
        InventoryRepository(db),
        order_repo=OrderRepository(db),
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

# ---------------------------------------------------------------------------
# Returns (admin moderation — controlled states, separate from payment state)
# ---------------------------------------------------------------------------

@router.get("/returns", response_model=List[ReturnResponse])
def list_returns(
    order_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    svc: ReturnService = Depends(get_return_service),
):
    return svc.list_all(current_user, order_id=order_id)


@router.get("/returns/{return_id}", response_model=ReturnResponse)
def get_return(
    return_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: ReturnService = Depends(get_return_service),
):
    return svc.get_return(return_id, current_user)


@router.post("/returns/{return_id}/approve", response_model=ReturnResponse)
def approve_return(
    return_id: str,
    payload: Optional[ReturnActionRequest] = None,
    current_user: User = Depends(get_current_active_user),
    svc: ReturnService = Depends(get_return_service),
):
    return svc.approve(return_id, current_user, reason=payload.reason if payload else None)


@router.post("/returns/{return_id}/reject", response_model=ReturnResponse)
def reject_return(
    return_id: str,
    payload: Optional[ReturnActionRequest] = None,
    current_user: User = Depends(get_current_active_user),
    svc: ReturnService = Depends(get_return_service),
):
    return svc.reject(return_id, current_user, reason=payload.reason if payload else None)


@router.post("/returns/{return_id}/receive", response_model=ReturnResponse)
def receive_return(
    return_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: ReturnService = Depends(get_return_service),
):
    return svc.mark_received(return_id, current_user)


@router.post("/returns/{return_id}/complete", response_model=ReturnResponse)
def complete_return(
    return_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: ReturnService = Depends(get_return_service),
):
    return svc.complete(return_id, current_user)


@router.post("/returns/{return_id}/refund")
def initiate_return_refund(
    return_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: ReturnService = Depends(get_return_service),
):
    """Initiate the DEMO refund for a completed return (idempotent)."""
    return svc.initiate_refund(return_id, current_user)


# ---------------------------------------------------------------------------
# Review moderation (approved reviews drive the published rating)
# ---------------------------------------------------------------------------

@router.get("/reviews", response_model=List[ReviewResponse])
def list_reviews_for_moderation(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_moderation_service),
):
    if status not in (None, "pending", "approved", "rejected"):
        from fastapi import HTTPException
        raise HTTPException(422, "status must be pending / approved / rejected")
    return svc.list_reviews_for_moderation(current_user, status)


@router.post("/reviews/{review_id}/moderate", response_model=ReviewResponse)
def moderate_review(
    review_id: str,
    payload: ReviewModerationUpdate,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_moderation_service),
):
    """approve / reject a review; approved reviews affect the product rating."""
    return svc.moderate_review(review_id, payload.action, current_user)