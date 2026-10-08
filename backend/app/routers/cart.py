"""Cart router — uses CartService with Inventory + Coupon repositories."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.schemas.cart import CartResponse
from app.schemas.coupon import CouponApply
from app.services.cart_service import CartService
from app.repositories.cart_repo import CartRepository
from app.repositories.coupon_repo import CouponRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.inventory_repo import InventoryRepository
from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/cart", tags=["cart"])


def get_cart_service(db: Session = Depends(get_db)) -> CartService:
    return CartService(
        CartRepository(db),
        ProductRepository(db),
        InventoryRepository(db),
        CouponRepository(db),
    )


@router.get("", response_model=CartResponse)
def get_cart(
    current_user: User = Depends(get_current_active_user),
    svc: CartService = Depends(get_cart_service),
):
    return svc.get_cart(current_user)


class CartItemPayload(BaseModel):
    product_id: str
    quantity: int = 1


@router.post("/add", response_model=CartResponse)
def add_to_cart(
    payload: CartItemPayload,
    current_user: User = Depends(get_current_active_user),
    svc: CartService = Depends(get_cart_service),
):
    return svc.add_item(payload.product_id, payload.quantity, current_user)


@router.put("/update", response_model=CartResponse)
def update_cart_item(
    payload: CartItemPayload,
    current_user: User = Depends(get_current_active_user),
    svc: CartService = Depends(get_cart_service),
):
    return svc.update_item(payload.product_id, payload.quantity, current_user)


@router.delete("/remove", response_model=CartResponse)
def remove_cart_item(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: CartService = Depends(get_cart_service),
):
    return svc.remove_item(product_id, current_user)


@router.post("/coupon", response_model=CartResponse)
def apply_coupon(
    payload: CouponApply,
    current_user: User = Depends(get_current_active_user),
    svc: CartService = Depends(get_cart_service),
):
    return svc.apply_coupon(payload.code, current_user)


@router.delete("/coupon", response_model=CartResponse)
def remove_coupon(
    current_user: User = Depends(get_current_active_user),
    svc: CartService = Depends(get_cart_service),
):
    return svc.remove_coupon(current_user)