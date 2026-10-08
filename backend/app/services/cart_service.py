"""Cart service — backend-authoritative pricing, stock validation, and coupon handling."""
from __future__ import annotations

from decimal import Decimal

from app.core.exceptions import (
    BadRequestException,
    NotFoundException,
)
from app.models.user import User
from app.repositories.cart_repo import CartRepository
from app.repositories.coupon_repo import CouponRepository
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.cart import CartResponse


class CartService:
    def __init__(
        self,
        cart_repo: CartRepository,
        product_repo: ProductRepository,
        inventory_repo: InventoryRepository,
        coupon_repo: CouponRepository,
    ):
        self.cart_repo = cart_repo
        self.product_repo = product_repo
        self.inventory_repo = inventory_repo
        self.coupon_repo = coupon_repo

    def _build_response(self, cart) -> CartResponse:
        """Recalculate subtotal/discount before returning. The frontend never
        supplies prices, discounts, or totals — everything is recomputed here."""
        self.cart_repo.calculate_subtotal(cart)
        response = CartResponse.model_validate(cart)
        response.item_count = len(cart.items)
        subtotal = Decimal(str(cart.subtotal))
        discount = Decimal(str(cart.discount_amount))
        # A discount must never exceed the subtotal (cart contents may change
        # between coupon application and checkout).
        if discount > subtotal:
            discount = subtotal
            cart.discount_amount = discount
        response.discount_amount = discount
        response.total = subtotal - discount
        response.coupon_code = cart.coupon.code if cart.coupon else None
        return response

    def _refresh_discount(self, cart) -> None:
        """Re-derive the stored discount from the attached coupon whenever cart
        contents change (add/update/remove/move). The frontend never knows the
        current applied amount — it is always recomputed server-side. Usage is
        still only recorded at checkout."""
        subtotal = self.cart_repo.calculate_subtotal(cart)
        if cart.coupon is not None and self.coupon_repo is not None:
            discount = self.coupon_repo.discount_for(cart.coupon, subtotal)
            if discount > subtotal:
                discount = subtotal
            self.cart_repo.set_coupon(cart, cart.coupon, discount)

    def get_cart(self, current_user: User) -> CartResponse:
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        return self._build_response(cart)

    def add_item(self, product_id: str, quantity: int, current_user: User) -> CartResponse:
        if quantity <= 0:
            raise BadRequestException("Quantity must be greater than 0")

        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        if not product.is_active:
            raise BadRequestException("Product is not available")

        # Stock validation
        inv = self.inventory_repo.get_by_product(product_id)
        available = inv.available_stock if inv else product.stock
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        existing = self.cart_repo.get_cart_item(cart.id, product_id)
        already_in_cart = existing.quantity if existing else 0
        if available < already_in_cart + quantity:
            raise BadRequestException(
                f"Insufficient stock. Available: {max(0, available - already_in_cart)}"
            )

        if existing:
            self.cart_repo.update_item_quantity(existing, existing.quantity + quantity)
        else:
            self.cart_repo.add_item(cart.id, product, quantity)

        self._refresh_discount(cart)
        return self._build_response(cart)

    def update_item(self, product_id: str, quantity: int, current_user: User) -> CartResponse:
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        item = self.cart_repo.get_cart_item(cart.id, product_id)

        if not item:
            raise NotFoundException("Product not in cart")

        if quantity <= 0:
            self.cart_repo.remove_item(item)
            self._refresh_discount(cart)
            return self._build_response(cart)

        # Stock validation
        product = self.product_repo.get_product(product_id)
        inv = self.inventory_repo.get_by_product(product_id)
        available = inv.available_stock if inv else (product.stock if product else 0)
        if available < quantity:
            raise BadRequestException(f"Insufficient stock. Available: {available}")

        self.cart_repo.update_item_quantity(item, quantity)
        self._refresh_discount(cart)
        return self._build_response(cart)

    def remove_item(self, product_id: str, current_user: User) -> CartResponse:
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        item = self.cart_repo.get_cart_item(cart.id, product_id)
        if item:
            self.cart_repo.remove_item(item)
        self._refresh_discount(cart)
        return self._build_response(cart)

    # ------------------------------------------------------------------
    # Coupons
    # ------------------------------------------------------------------

    def apply_coupon(self, code: str, current_user: User) -> CartResponse:
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        if not cart.items:
            raise BadRequestException("Cart is empty — add items before applying a coupon")
        coupon = self.coupon_repo.get_by_code(code)
        if not coupon:
            raise NotFoundException(f"Coupon code '{code.strip().upper()}' not found")

        subtotal = self.cart_repo.calculate_subtotal(cart)
        if not self.coupon_repo.is_usable(coupon, current_user.id, subtotal):
            raise BadRequestException("Coupon is not applicable to this cart")

        # Usage is recorded at checkout, not here, so applying/removing a coupon
        # while shopping does not consume it.
        discount = self.coupon_repo.discount_for(coupon, subtotal)
        self.cart_repo.set_coupon(cart, coupon, discount)
        return self._build_response(cart)

    def remove_coupon(self, current_user: User) -> CartResponse:
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        if cart.coupon_id:
            self.cart_repo.clear_coupon(cart)
        return self._build_response(cart)
