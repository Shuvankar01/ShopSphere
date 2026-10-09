"""Payment router — DEMO payment endpoints with real authorization + persistence.

Flow: POST /create records a pending demo transaction -> the frontend performs a
demo success/failure/cancel action (POST /{transaction_id}/complete) or a local
demo webhook (POST /webhook) delivers an event. The server re-validates the
existing transaction before any state change; a client can never simply mark an
order as paid. No real payment provider, keys or webhook signatures are used.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.repositories.order_repo import OrderRepository
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import (
    PaymentCompleteRequest,
    PaymentCreate,
    PaymentResponse,
    WebhookEvent,
)
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
    """Create a DEMO payment transaction for an order the current user owns.

    Errors: 404 unknown/foreign order, 409 already paid / already in progress /
    cancelled, 422 invalid payment method.
    """
    return svc.create_payment(payload, current_user)


@router.post("/{transaction_id}/complete", response_model=PaymentResponse)
def complete_payment(
    transaction_id: str,
    payload: PaymentCompleteRequest,
    current_user: User = Depends(get_current_active_user),
    svc: PaymentService = Depends(get_payment_service),
):
    """Frontend performs a DEMO action (success / failure / cancel). The server
    validates the existing transaction and then updates payment + order state."""
    return svc.complete_payment(transaction_id, payload, current_user)


@router.post("/webhook")
def payment_webhook(
    event: WebhookEvent,
    svc: PaymentService = Depends(get_payment_service),
):
    """Local/demo webhook only — no signature verification. Idempotent: a
    duplicate event whose target state is already reached is acknowledged
    without reprocessing."""
    return svc.handle_webhook(event)