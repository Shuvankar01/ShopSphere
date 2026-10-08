"""Cart repository — Decimal-safe calculations, stock-validated operations."""
from __future__ import annotations
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.models.cart import Cart, CartItem
from app.models.coupon import Coupon
from app.models.product import Product


class CartRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_cart_by_user(self, user_id: str) -> Cart:
        cart = self.db.query(Cart).filter(Cart.user_id == user_id).first()
        if not cart:
            cart = Cart(user_id=user_id, subtotal=Decimal("0.00"))
            self.db.add(cart)
            self.db.commit()
            self.db.refresh(cart)
        return cart

    def get_cart_item(self, cart_id: str, product_id: str) -> Optional[CartItem]:
        return (
            self.db.query(CartItem)
            .filter(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
            .first()
        )

    def add_item(self, cart_id: str, product: Product, quantity: int) -> CartItem:
        unit_price = product.discount_price if product.discount_price is not None else product.price
        item = CartItem(
            cart_id=cart_id,
            product_id=product.id,
            quantity=quantity,
            unit_price=unit_price,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_item_quantity(self, item: CartItem, quantity: int) -> None:
        item.quantity = quantity
        self.db.commit()
        self.db.refresh(item)

    def remove_item(self, item: CartItem) -> None:
        self.db.delete(item)
        self.db.commit()

    def calculate_subtotal(self, cart: Cart) -> Decimal:
        """Recalculate subtotal from current prices (backend authoritative)."""
        total = Decimal("0.00")
        for item in cart.items:
            product = item.product
            price = product.discount_price if product.discount_price is not None else product.price
            total += Decimal(str(price)) * item.quantity
        cart.subtotal = total
        self.db.commit()
        return total

    # ------------------------------------------------------------------
    # Coupons
    # ------------------------------------------------------------------

    def set_coupon(self, cart: Cart, coupon: Coupon, discount_amount: Decimal) -> None:
        cart.coupon_id = coupon.id
        cart.discount_amount = discount_amount
        self.db.commit()
        self.db.refresh(cart)

    def clear_coupon(self, cart: Cart) -> None:
        cart.coupon_id = None
        cart.discount_amount = Decimal("0.00")
        self.db.commit()
        self.db.refresh(cart)

    def clear_cart(self, cart: Cart) -> None:
        for item in cart.items:
            self.db.delete(item)
        cart.subtotal = Decimal("0.00")
        cart.discount_amount = Decimal("0.00")
        cart.coupon_id = None
        # No commit — the caller owns the transaction (atomic checkout).
