"""Returns (RMA) router — customer request/view/cancel; admin moderation lives
in the admin router. Return state is separate from payment state."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.repositories.order_repo import OrderRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.return_repo import ReturnRepository
from app.schemas.return_request import ReturnCreate, ReturnResponse
from app.services.refund_service import RefundService
from app.services.return_service import ReturnService

router = APIRouter(prefix="/returns", tags=["returns"])


def get_return_service(db: Session = Depends(get_db)) -> ReturnService:
    return ReturnService(
        return_repo=ReturnRepository(db),
        order_repo=OrderRepository(db),
        payment_repo=PaymentRepository(db),
        refund_service=RefundService(OrderRepository(db), PaymentRepository(db)),
    )


@router.post("", response_model=ReturnResponse, status_code=201)
def create_return(
    data: ReturnCreate,
    current_user: User = Depends(get_current_active_user),
    svc: ReturnService = Depends(get_return_service),
):
    return svc.create_return(data, current_user)


@router.get("", response_model=List[ReturnResponse])
def list_returns(
    current_user: User = Depends(get_current_active_user),
    svc: ReturnService = Depends(get_return_service),
):
    return svc.list_returns(current_user)


@router.get("/{return_id}", response_model=ReturnResponse)
def get_return(
    return_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: ReturnService = Depends(get_return_service),
):
    return svc.get_return(return_id, current_user)


@router.post("/{return_id}/cancel", response_model=ReturnResponse)
def cancel_return(
    return_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: ReturnService = Depends(get_return_service),
):
    return svc.cancel_return(return_id, current_user)