"""Payment router — demo payment endpoint with real authorization + persistence."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.repositories.order_repo import OrderRepository
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payment", tags=["payment"])


def get_payment_service(db: Session = Depends(get_db)) -> PaymentService:
    return PaymentService(OrderRepository(db), PaymentRepository(db))


@router.post("/create", response_model=PaymentResponse)
def create_payment(
    payload: PaymentCreate,
    current_user: User = Depends(get_current_active_user),
    svc: PaymentService = Depends(get_payment_service),
):
    """Pay an order the current user owns.

    Errors: 404 unknown/foreign order, 409 already paid / refunded / cancelled,
    422 invalid payment method.
    """
    return svc.create_payment(payload, current_user)
