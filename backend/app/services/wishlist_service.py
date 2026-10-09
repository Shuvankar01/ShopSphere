"""Wishlist service."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from app.models.user import User
from app.repositories.cart_repo import CartRepository
from app.repositories.coupon_repo import CouponRepository
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.wishlist_repo import WishlistRepository
from app.schemas.cart import CartResponse
from app.schemas.wishlist import WishlistResponse
from app.services.cart_service import cart_coupon_lines


class WishlistService:
    def __init__(
        self,
        wishlist_repo: WishlistRepository,
        product_repo: ProductRepository,
        cart_repo: CartRepository,
        inventory_repo: InventoryRepository,
        coupon_repo: Optional[CouponRepository] = None,
    ):
        self.wishlist_repo = wishlist_repo
        self.product_repo = product_repo
        self.cart_repo = cart_repo
        self.inventory_repo = inventory_repo
        self.coupon_repo = coupon_repo

    def get_wishlist(self, current_user: User) -> WishlistResponse:
        wishlist = self.wishlist_repo.get_by_user(current_user.id)
        return WishlistResponse.model_validate(wishlist)

    def add_item(self, product_id: str, current_user: User) -> WishlistResponse:
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        # Deactivated or removed products cannot be added to a wishlist.
        if not product.is_active:
            raise BadRequestException("Product is no longer available")

        wishlist = self.wishlist_repo.get_by_user(current_user.id)
        if self.wishlist_repo.get_item(wishlist.id, product_id):
            raise ConflictException("Product already in wishlist")

        self.wishlist_repo.add_item(wishlist.id, product_id)
        # Reload with relationships
        wishlist = self.wishlist_repo.get_by_user(current_user.id)
        return WishlistResponse.model_validate(wishlist)

    def remove_item(self, product_id: str, current_user: User) -> WishlistResponse:
        wishlist = self.wishlist_repo.get_by_user(current_user.id)
        item = self.wishlist_repo.get_item(wishlist.id, product_id)
        if item:
            self.wishlist_repo.remove_item(item)
        wishlist = self.wishlist_repo.get_by_user(current_user.id)
        return WishlistResponse.model_validate(wishlist)

    def move_to_cart(self, product_id: str, quantity: int, current_user: User) -> CartResponse:
        """Move a wishlist item to cart and remove from wishlist."""
        if quantity <= 0:
            raise BadRequestException("Quantity must be greater than 0")
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        if not product.is_active:
            raise BadRequestException("Product is no longer available")

        inv = self.inventory_repo.get_by_product(product_id)
        available = inv.available_stock if inv else product.stock
        if available < quantity:
            raise BadRequestException(f"Insufficient stock. Available: {available}")

        # Add to cart
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        existing = self.cart_repo.get_cart_item(cart.id, product_id)
        if existing:
            self.cart_repo.update_item_quantity(existing, existing.quantity + quantity)
        else:
            self.cart_repo.add_item(cart.id, product, quantity)

        # Remove from wishlist
        wishlist = self.wishlist_repo.get_by_user(current_user.id)
        item = self.wishlist_repo.get_item(wishlist.id, product_id)
        if item:
            self.wishlist_repo.remove_item(item)

        # Backend-authoritative totals (including any applied coupon discount,
        # recomputed against the post-move subtotal so the amounts stay live).
        subtotal = self.cart_repo.calculate_subtotal(cart)
        discount = Decimal("0.00")
        if cart.coupon is not None and self.coupon_repo is not None:
            lines = cart_coupon_lines(cart)
            discount = self.coupon_repo.discount_for(cart.coupon, subtotal, lines)
            if discount > subtotal:
                discount = subtotal
            self.cart_repo.set_coupon(cart, cart.coupon, discount)
        response = CartResponse.model_validate(cart)
        response.item_count = len(cart.items)
        response.discount_amount = discount
        response.total = subtotal - discount
        response.coupon_code = cart.coupon.code if cart.coupon else None
        return response
