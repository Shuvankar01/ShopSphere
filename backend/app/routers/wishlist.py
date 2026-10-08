"""Wishlist router."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.wishlist import WishlistResponse, WishlistAddItem, MoveToCart
from app.schemas.cart import CartResponse
from app.services.wishlist_service import WishlistService
from app.repositories.wishlist_repo import WishlistRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.cart_repo import CartRepository
from app.repositories.coupon_repo import CouponRepository
from app.repositories.inventory_repo import InventoryRepository
from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


def get_wishlist_service(db: Session = Depends(get_db)) -> WishlistService:
    return WishlistService(
        WishlistRepository(db),
        ProductRepository(db),
        CartRepository(db),
        InventoryRepository(db),
        CouponRepository(db),
    )


@router.get("", response_model=WishlistResponse)
def get_wishlist(
    current_user: User = Depends(get_current_active_user),
    svc: WishlistService = Depends(get_wishlist_service),
):
    return svc.get_wishlist(current_user)


@router.post("/add", response_model=WishlistResponse, status_code=201)
def add_to_wishlist(
    payload: WishlistAddItem,
    current_user: User = Depends(get_current_active_user),
    svc: WishlistService = Depends(get_wishlist_service),
):
    return svc.add_item(payload.product_id, current_user)


@router.delete("/remove/{product_id}", response_model=WishlistResponse)
def remove_from_wishlist(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: WishlistService = Depends(get_wishlist_service),
):
    return svc.remove_item(product_id, current_user)


@router.post("/move-to-cart", response_model=CartResponse)
def move_to_cart(
    payload: MoveToCart,
    current_user: User = Depends(get_current_active_user),
    svc: WishlistService = Depends(get_wishlist_service),
):
    return svc.move_to_cart(payload.product_id, payload.quantity, current_user)
