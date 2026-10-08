"""Order service — creates orders with atomic inventory reservation."""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.core.logging import logger
from app.models.coupon import CouponUsage
from app.models.user import User
from app.repositories.cart_repo import CartRepository
from app.repositories.coupon_repo import CouponRepository
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.order_repo import OrderRepository
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate

VALID_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"shipped", "cancelled"},
    "shipped": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}


class OrderService:
    def __init__(
        self,
        order_repo: OrderRepository,
        cart_repo: CartRepository,
        inventory_repo: InventoryRepository,
        coupon_repo: Optional[CouponRepository] = None,
    ):
        self.order_repo = order_repo
        self.cart_repo = cart_repo
        self.inventory_repo = inventory_repo
        self.coupon_repo = coupon_repo

    def create_order(self, order_in: OrderCreate, current_user: User) -> OrderResponse:
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        if not cart.items:
            raise BadRequestException("Cart is empty")

        # Recalculate backend-authoritative item total (frontend values ignored).
        item_total = Decimal("0.00")
        items_data = []
        for item in cart.items:
            product = item.product
            if not product or not product.is_active:
                raise BadRequestException(f"Product '{item.product_id}' is no longer available")
            price = product.discount_price if product.discount_price is not None else product.price
            price = Decimal(str(price))
            item_total += price * item.quantity
            items_data.append({
                "product_id": product.id,
                "product_name": product.name,
                "quantity": item.quantity,
                "price": price,
            })

        # Apply the cart's coupon (if any) — revalidated at checkout so a
        # coupon that expired/ran out between apply and checkout cannot slip in.
        discount = Decimal("0.00")
        coupon_id = None
        if cart.coupon is not None and self.coupon_repo is not None:
            if self.coupon_repo.is_usable(cart.coupon, current_user.id, item_total):
                discount = self.coupon_repo.discount_for(cart.coupon, item_total)
                coupon_id = cart.coupon.id
            else:
                logger.info(
                    f"Coupon {cart.coupon.code} no longer usable at checkout for user {current_user.id}"
                )
        total = item_total - discount

        # Build the order row first so its id can anchor inventory reservations.
        order = self.order_repo.create_order(
            order_in, current_user.id, total,
            coupon_id=coupon_id, discount_amount=discount,
        )
        self.order_repo.add_status_history(
            order_id=order.id,
            from_status=None,
            to_status=order.order_status,
            changed_by=current_user.id,
            note="Order placed",
        )

        # Reserve inventory for each item atomically (row-level locks prevent
        # two simultaneous customers from buying the last unit).
        reserved = []
        try:
            for item_data in items_data:
                inv = self.inventory_repo.get_by_product(
                    item_data["product_id"], for_update=True
                )
                if inv is None:
                    raise BadRequestException(
                        f"Product '{item_data['product_id']}' has no inventory record"
                    )
                self.inventory_repo.reserve(
                    inv,
                    quantity=item_data["quantity"],
                    reference_id=order.id,
                    reference_type="order",
                )
                reserved.append((inv, item_data["quantity"]))
        except (ValueError, BadRequestException) as e:
            # Atomic failure: roll back the order + any reserves made this loop.
            self.inventory_repo.db.rollback()
            raise BadRequestException(str(e)) from None

        for item_data in items_data:
            self.order_repo.add_order_item(
                order_id=order.id,
                product_id=item_data["product_id"],
                product_name=item_data["product_name"],
                quantity=item_data["quantity"],
                price=item_data["price"],
            )

        # Bind the coupon usage to this order (one use per customer per coupon).
        if coupon_id and self.coupon_repo is not None:
            self.coupon_repo.record_usage(cart.coupon, current_user.id, discount)
            usage = self.coupon_repo.db.query(CouponUsage).filter(
                CouponUsage.coupon_id == coupon_id,
                CouponUsage.user_id == current_user.id,
            ).first()
            if usage:
                usage.order_id = order.id

        self.cart_repo.clear_cart(cart)
        # Single commit: order, items, history, usage, reservations, and cart
        # clear all become visible together.
        self.inventory_repo.db.commit()

        logger.info(f"Order {order.id} created for user {current_user.id} total={total}")
        return OrderResponse.model_validate(order)

    def get_user_orders(self, current_user: User) -> List[OrderResponse]:
        orders = self.order_repo.get_user_orders(current_user.id)
        return [OrderResponse.model_validate(o) for o in orders]

    def get_order(self, order_id: str, current_user: User) -> OrderResponse:
        order = self.order_repo.get_order(order_id)
        if not order:
            raise NotFoundException("Order not found")
        # Owner or admin only. Sellers must not read arbitrary customer orders
        # (IDOR): a non-existent order and a foreign order both return 404 so
        # order ids cannot be probed.
        if order.user_id != current_user.id and current_user.role != "admin":
            raise NotFoundException("Order not found")
        return OrderResponse.model_validate(order)

    def update_order_status(
        self, order_id: str, status_update: OrderStatusUpdate, current_user: User
    ) -> OrderResponse:
        # Admin only: sellers may not touch orders for other sellers' products,
        # and customers may not change fulfillment state themselves.
        if current_user.role != "admin":
            raise ForbiddenException("Not authorized to update order status")

        order = self.order_repo.get_order(order_id)
        if not order:
            raise NotFoundException("Order not found")

        new_status = status_update.status
        allowed = VALID_TRANSITIONS.get(order.order_status, set())
        if new_status not in allowed:
            raise BadRequestException(
                f"Cannot transition order from '{order.order_status}' to '{new_status}'. "
                f"Allowed: {sorted(allowed) or 'none'}"
            )

        # If cancelling, release reserved stock
        if new_status == "cancelled":
            for item in order.items:
                inv = self.inventory_repo.get_by_product(item.product_id, for_update=True)
                if inv:
                    self.inventory_repo.release(inv, item.quantity, reference_id=order.id, reference_type="order_cancel")

        # If shipping (fulfilling), deduct stock
        if new_status == "shipped":
            for item in order.items:
                inv = self.inventory_repo.get_by_product(item.product_id, for_update=True)
                if inv:
                    try:
                        self.inventory_repo.deduct(inv, item.quantity, reference_id=order.id, reference_type="order_shipped")
                    except ValueError as e:
                        raise BadRequestException(str(e)) from None

        old_status = order.order_status
        self.order_repo.add_status_history(
            order_id=order.id,
            from_status=old_status,
            to_status=new_status,
            changed_by=current_user.id,
        )
        self.order_repo.update_order_status(order, new_status)
        self.inventory_repo.db.commit()
        logger.info(f"Order {order.id} status → {new_status} by user {current_user.id}")
        return OrderResponse.model_validate(order)
