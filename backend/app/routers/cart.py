from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.schemas.cart import CartResponse
from app.services.cart_service import CartService
from app.repositories.cart_repo import CartRepository
from app.repositories.product_repo import ProductRepository
from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/cart", tags=["cart"])

def get_cart_service(db: Session = Depends(get_db)) -> CartService:
    return CartService(CartRepository(db), ProductRepository(db))

@router.get("", response_model=CartResponse)
def get_cart(
    current_user: User = Depends(get_current_active_user),
    cart_service: CartService = Depends(get_cart_service)
):
    return cart_service.get_cart(current_user)

class CartItemPayload(BaseModel):
    product_id: str
    quantity: int

@router.post("/add", response_model=CartResponse)
def add_to_cart(
    payload: CartItemPayload,
    current_user: User = Depends(get_current_active_user),
    cart_service: CartService = Depends(get_cart_service)
):
    return cart_service.add_item(payload.product_id, payload.quantity, current_user)

@router.put("/update", response_model=CartResponse)
def update_cart_item(
    payload: CartItemPayload,
    current_user: User = Depends(get_current_active_user),
    cart_service: CartService = Depends(get_cart_service)
):
    return cart_service.update_item(payload.product_id, payload.quantity, current_user)

@router.delete("/remove", response_model=CartResponse)
def remove_cart_item(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    cart_service: CartService = Depends(get_cart_service)
):
    return cart_service.remove_item(product_id, current_user)
