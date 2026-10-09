"""Demo refunds router (admin). Refunds belong to a captured payment, never
exceed it, are idempotent, and update order/payment state consistently."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.repositories.order_repo import OrderRepository
from app.repositories.payment_repo import PaymentRepository
from app.schemas.refund import RefundCreate, RefundResponse
from app.services.refund_service import RefundService

router = APIRouter(prefix="/refunds", tags=["refunds"])


def get_refund_service(db: Session = Depends(get_db)) -> RefundService:
    return RefundService(OrderRepository(db), PaymentRepository(db))


@router.post("", response_model=RefundResponse, status_code=201)
def create_refund(
    data: RefundCreate,
    current_user: User = Depends(get_current_active_user),
    svc: RefundService = Depends(get_refund_service),
):
    """Admin-only. DEMO refund against the order's captured payment. Pass an
    idempotency_key to make repeated submissions harmless."""
    return svc.create_refund(data, current_user)


@router.get("", response_model=List[RefundResponse])
def list_refunds(
    order_id: str | None = None,
    current_user: User = Depends(get_current_active_user),
    svc: RefundService = Depends(get_refund_service),
):
    return svc.list_refunds(current_user, order_id=order_id)


@router.get("/{refund_id}", response_model=RefundResponse)
def get_refund(
    refund_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: RefundService = Depends(get_refund_service),
):
    return svc.get_refund(refund_id, current_user)


@router.post("/{refund_id}/process", response_model=RefundResponse)
def process_refund(
    refund_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: RefundService = Depends(get_refund_service),
):
    """Idempotent demo processing step (also reachable via the demo webhook)."""
    return svc.process_refund(refund_id, current_user)