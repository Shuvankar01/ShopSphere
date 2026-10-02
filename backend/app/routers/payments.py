from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid
from app.database.session import get_db
from app.repositories.order_repo import OrderRepository
from app.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/payment", tags=["payment"])

class PaymentCreate(BaseModel):
    order_id: str
    payment_method: str

class PaymentResponse(BaseModel):
    transaction_id: str
    status: str
    redirect_url: Optional[str] = None

@router.post("/create", response_model=PaymentResponse)
def create_payment(
    payload: PaymentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # This is a mock payment integration to satisfy the frontend contract
    order_repo = OrderRepository(db)
    order = order_repo.get_order(payload.order_id)
    
    if order and order.user_id == current_user.id:
        # Mark as paid immediately for mock purposes
        order_repo.update_payment_status(order, "paid")
        order_repo.update_order_status(order, "confirmed")
        
    return PaymentResponse(
        transaction_id=f"txn_{uuid.uuid4().hex[:12]}",
        status="success",
        redirect_url=None
    )
