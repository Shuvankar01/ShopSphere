"""Order service — atomic checkout with backend-authoritative totals, a
controlled order lifecycle, and DEMO payment coordination.

The frontend never supplies amounts: subtotal, coupon discount, tax, shipping
and the grand total are all computed here. Order creation, inventory
reservation, coupon usage recording and the cart clear share one transaction.
"""
from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.core.logging import logger
from app.models.order import Order
from app.models.user import User
from app.repositories.address_repo import AddressRepository
from app.repositories.cart_repo import CartRepository
from app.repositories.coupon_repo import CouponLine, CouponRepository
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.payment_repo import PaymentRepository
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
)
from app.services import shipping

# Controlled order lifecycle. No arbitrary strings — every move must be in the table.
VALID_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"processing", "cancelled"},
    "processing": {"packed", "cancelled"},
    "packed": {"shipped", "cancelled"},
    "shipped": {"out_for_delivery"},
    "out_for_delivery": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}

# Customers may cancel only before the order ships.
CUSTOMER_CANCELLABLE = {"pending", "confirmed", "processing", "packed"}

_SHIPMENT_STATUS_BY_ORDER = {
    "shipped": "shipped",
    "out_for_delivery": "out_for_delivery",
    "delivered": "delivered",
    "cancelled": "cancelled",
}


def _money(value) -> Decimal:
    return Decimal(str(value))


def compute_tax(taxable_amount: Decimal) -> Decimal:
    rate = Decimal(str(settings.TAX_RATE))
    return (taxable_amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class OrderService:
    def __init__(
        self,
        order_repo: OrderRepository,
        cart_repo: CartRepository,
        inventory_repo: InventoryRepository,
        coupon_repo: Optional[CouponRepository] = None,
        payment_repo: Optional[PaymentRepository] = None,
        address_repo: Optional[AddressRepository] = None,
    ):
        self.order_repo = order_repo
        self.cart_repo = cart_repo
        self.inventory_repo = inventory_repo
        self.coupon_repo = coupon_repo
        self.payment_repo = payment_repo
        self.address_repo = address_repo

    # ------------------------------------------------------------------
    # Checkout
    # ------------------------------------------------------------------

    @staticmethod
    def format_address_snapshot(snapshot: dict) -> str:
        parts = [
            snapshot.get("recipient_name"),
            snapshot.get("line1"),
            snapshot.get("line2"),
        ]
        city_state = ", ".join(x for x in [snapshot.get("city"), snapshot.get("state")] if x)
        line = ", ".join(x for x in [city_state, snapshot.get("postal_code")] if x)
        parts.append(line)
        if snapshot.get("country"):
            parts.append(snapshot["country"])
        return ", ".join(x for x in parts if x)

    def _resolve_address(
        self, order_in: OrderCreate, user_id: str
    ) -> tuple[str, Optional[str]]:
        """Return (formatted_address, snapshot_json). The snapshot is immutable:
        later address-book edits cannot alter historical orders."""
        if order_in.shipping_address_id:
            if self.address_repo is None:
                raise BadRequestException("Address lookup unavailable")
            address = self.address_repo.get_user_address(
                user_id, order_in.shipping_address_id
            )
            if not address:
                raise BadRequestException("Saved shipping address not found")
            snapshot = {
                "label": address.label,
                "recipient_name": address.recipient_name,
                "phone": address.phone,
                "line1": address.line1,
                "line2": address.line2,
                "city": address.city,
                "state": address.state,
                "postal_code": address.postal_code,
                "country": address.country,
            }
            return self.format_address_snapshot(snapshot), json.dumps(snapshot, ensure_ascii=False)
        formatted = order_in.shipping_address or ""
        return formatted, json.dumps({"raw": formatted}, ensure_ascii=False)

    def _compute_pricing(self, cart, user_id: str, shipping_method: str) -> dict:
        """Single source of truth for checkout money math, shared by order
        creation and the pre-checkout quote. The client never supplies amounts:
        line prices are reloaded from the product rows and every total is
        recomputed here."""
        method = shipping.require_shipping_method(shipping_method)
        shipping_cost = method["charge"]

        item_total = Decimal("0.00")
        items_data = []
        coupon_lines: List[CouponLine] = []
        for item in cart.items:
            product = item.product
            if not product or not product.is_active:
                raise BadRequestException(
                    f"Product '{item.product_id}' is no longer available"
                )
            price = (
                product.discount_price
                if product.discount_price is not None
                else product.price
            )
            price = _money(price)
            item_total += price * item.quantity
            items_data.append(
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "quantity": item.quantity,
                    "price": price,
                }
            )
            coupon_lines.append(
                CouponLine(
                    id=product.id,
                    category_id=product.category_id,
                    price=price,
                    discount_price=(
                        product.discount_price
                        if product.discount_price is not None
                        else None
                    ),
                    quantity=item.quantity,
                    is_active=product.is_active,
                )
            )

        # Re-validate the cart coupon at checkout (expiry/limits/restrictions).
        discount = Decimal("0.00")
        coupon = cart.coupon
        coupon_id = None
        if coupon is not None and self.coupon_repo is not None:
            if self.coupon_repo.is_usable(coupon, user_id, item_total, coupon_lines):
                discount = self.coupon_repo.discount_for(coupon, item_total, coupon_lines)
                coupon_id = coupon.id
            else:
                logger.info(
                    f"Coupon {coupon.code} no longer usable at checkout for user {user_id}"
                )

        # Backend-computed totals: subtotal, tax on (subtotal - discount), shipping.
        taxable = item_total - discount
        tax_amount = compute_tax(taxable)
        total = taxable + tax_amount + shipping_cost
        return {
            "method": method,
            "shipping_cost": shipping_cost,
            "items_data": items_data,
            "coupon_lines": coupon_lines,
            "coupon": coupon if coupon_id else None,
            "coupon_id": coupon_id,
            "subtotal": item_total,
            "discount": discount,
            "tax_amount": tax_amount,
            "total": total,
        }

    def quote_checkout(self, shipping_method: str, current_user: User) -> dict:
        """Pre-checkout totals for the current cart + chosen shipping method.
        Display-only: the amounts are recomputed and re-validated at order time."""
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        if not cart.items:
            raise BadRequestException("Cart is empty")
        pricing = self._compute_pricing(cart, current_user.id, shipping_method)
        method = pricing["method"]
        return {
            "subtotal": pricing["subtotal"],
            "discount_amount": pricing["discount"],
            "tax_amount": pricing["tax_amount"],
            "shipping_cost": pricing["shipping_cost"],
            "total_amount": pricing["total"],
            "shipping_method": method["code"],
            "shipping_method_name": method["name"],
            "estimated_delivery": shipping.estimate_delivery(method["code"]),
            "coupon_code": pricing["coupon"].code if pricing["coupon"] else None,
            "currency": settings.CURRENCY,
        }

    def create_order(self, order_in: OrderCreate, current_user: User) -> OrderResponse:
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        if not cart.items:
            raise BadRequestException("Cart is empty")

        # Resolve + snapshot the shipping address (immutable for the order).
        shipping_address, snapshot_json = self._resolve_address(order_in, current_user.id)

        # Backend-authoritative pricing (shared with the quote endpoint).
        pricing = self._compute_pricing(cart, current_user.id, order_in.shipping_method)
        items_data = pricing["items_data"]
        coupon_lines = pricing["coupon_lines"]
        coupon = pricing["coupon"]
        coupon_id = pricing["coupon_id"]

        order = self.order_repo.create_order(
            order_in,
            current_user.id,
            subtotal=pricing["subtotal"],
            discount_amount=pricing["discount"],
            tax_amount=pricing["tax_amount"],
            shipping_cost=pricing["shipping_cost"],
            total_amount=pricing["total"],
            shipping_method=order_in.shipping_method,
            shipping_address=shipping_address,
            shipping_address_snapshot=snapshot_json,
            coupon_id=coupon_id,
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

        # Consume the coupon under a row lock (concurrency-safe against overuse).
        if coupon_id and self.coupon_repo is not None:
            try:
                self.coupon_repo.record_usage(
                    coupon,
                    current_user.id,
                    pricing["discount"],
                    subtotal=pricing["subtotal"],
                    items=coupon_lines,
                    order_id=order.id,
                )
            except BadRequestException as e:
                self.inventory_repo.db.rollback()
                raise

        self.cart_repo.clear_cart(cart)
        # Single commit: order, items, history, usage, reservations, cart clear.
        self.inventory_repo.db.commit()

        logger.info(
            f"Order {order.id} created for user {current_user.id} "
            f"subtotal={pricing['subtotal']} discount={pricing['discount']} "
            f"tax={pricing['tax_amount']} shipping={pricing['shipping_cost']} "
            f"total={pricing['total']} method={order_in.shipping_method}"
        )
        return OrderResponse.model_validate(order)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_user_orders(self, current_user: User) -> List[OrderResponse]:
        orders = self.order_repo.get_user_orders(current_user.id)
        return [OrderResponse.model_validate(o) for o in orders]

    def get_order(self, order_id: str, current_user: User) -> OrderResponse:
        order = self.order_repo.get_order(order_id)
        if not order:
            raise NotFoundException("Order not found")
        # Owner or admin only (IDOR-safe: foreign orders look like missing ones).
        if order.user_id != current_user.id and current_user.role != "admin":
            raise NotFoundException("Order not found")
        return OrderResponse.model_validate(order)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def can_transition(self, current_status: str, new_status: str) -> bool:
        return new_status in VALID_TRANSITIONS.get(current_status, set())

    def _leave_admin_only(self, current_user: User) -> None:
        if current_user.role != "admin":
            raise ForbiddenException("Not authorized to update order status")

    def _release_stock(self, order: Order, reference_type: str = "order_cancel") -> None:
        for item in order.items:
            inv = self.inventory_repo.get_by_product(item.product_id, for_update=True)
            if inv:
                self.inventory_repo.release(
                    inv, item.quantity, reference_id=order.id, reference_type=reference_type
                )

    def _deduct_stock(self, order: Order) -> None:
        for item in order.items:
            inv = self.inventory_repo.get_by_product(item.product_id, for_update=True)
            if inv:
                try:
                    self.inventory_repo.deduct(
                        inv, item.quantity, reference_id=order.id, reference_type="order_shipped"
                    )
                except ValueError as e:
                    raise BadRequestException(str(e)) from None

    def _auto_refund_if_paid(self, order: Order) -> None:
        """Cancelling an already-paid order returns the money via the DEMO
        provider automatically (no real money moves)."""
        if order.payment_status != "paid" or self.payment_repo is None:
            return
        payment = next(
            (p for p in self.payment_repo.get_payments_for_order(order.id) if p.status == "succeeded"),
            None,
        )
        if payment is None:
            return
        refund = self.payment_repo.create_refund(payment, _money(order.total_amount), reason="Order cancelled")
        self.payment_repo.complete_refund(refund, payment, order)

    def cancel_order(self, order_id: str, current_user: User, reason: Optional[str] = None) -> OrderResponse:
        order = self.order_repo.get_order(order_id)
        if not order:
            raise NotFoundException("Order not found")
        owner = order.user_id == current_user.id
        admin = current_user.role == "admin"
        if not (owner or admin):
            raise NotFoundException("Order not found")
        if not owner and not admin:
            raise ForbiddenException("Not authorized to cancel this order")
        if order.order_status not in CUSTOMER_CANCELLABLE:
            raise BadRequestException(
                f"Order cannot be cancelled from state '{order.order_status}'"
            )

        old_status = order.order_status
        self._release_stock(order)
        self._auto_refund_if_paid(order)
        self.order_repo.set_shipment_status(order, "cancelled")
        self.order_repo.update_order_status(order, "cancelled")
        self.order_repo.add_status_history(
            order_id=order.id,
            from_status=old_status,
            to_status="cancelled",
            changed_by=current_user.id,
            note=reason or "Cancelled",
        )
        self.inventory_repo.db.commit()
        logger.info(f"Order {order.id} cancelled by user {current_user.id}")
        return OrderResponse.model_validate(order)

    def update_order_status(
        self, order_id: str, status_update: OrderStatusUpdate, current_user: User
    ) -> OrderResponse:
        # Admin only: sellers may not touch orders for other sellers' products,
        # and customers may not move fulfillment state themselves (they cancel).
        self._leave_admin_only(current_user)

        order = self.order_repo.get_order(order_id)
        if not order:
            raise NotFoundException("Order not found")

        new_status = status_update.status
        if not self.can_transition(order.order_status, new_status):
            allowed = VALID_TRANSITIONS.get(order.order_status, set())
            raise BadRequestException(
                f"Cannot transition order from '{order.order_status}' to '{new_status}'. "
                f"Allowed: {sorted(allowed) or 'none'}"
            )

        if new_status == "cancelled":
            self._release_stock(order)
            self._auto_refund_if_paid(order)
        if new_status == "shipped":
            self._deduct_stock(order)
            self.order_repo.set_tracking(
                order, shipping.generate_tracking_number(order.id)
            )
        shipment_status = _SHIPMENT_STATUS_BY_ORDER.get(new_status)
        if shipment_status:
            self.order_repo.set_shipment_status(order, shipment_status)

        old_status = order.order_status
        self.order_repo.add_status_history(
            order_id=order.id,
            from_status=old_status,
            to_status=new_status,
            changed_by=current_user.id,
            note=status_update.reason,
        )
        self.order_repo.update_order_status(order, new_status)
        self.inventory_repo.db.commit()
        logger.info(f"Order {order.id} status → {new_status} by user {current_user.id}")
        return OrderResponse.model_validate(order)