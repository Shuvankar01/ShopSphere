from decimal import Decimal
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem, OrderStatusHistory
from app.schemas.order import OrderCreate


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_order(self, order_id: str) -> Order | None:
        return self.db.query(Order).filter(Order.id == order_id).first()

    def get_user_orders(self, user_id: str) -> List[Order]:
        return self.db.query(Order).filter(Order.user_id == user_id).order_by(desc(Order.created_at)).all()

    def get_all_orders(self) -> List[Order]:
        return self.db.query(Order).order_by(desc(Order.created_at)).all()

    def get_total_count(self) -> int:
        return self.db.query(Order).count()

    def get_total_revenue(self) -> Decimal:
        from sqlalchemy.sql import func
        total = self.db.query(func.sum(Order.total_amount)).filter(Order.payment_status == 'paid').scalar()
        return Decimal(total) if total is not None else Decimal("0.00")

    def get_recent_orders(self, limit: int = 5) -> List[Order]:
        return self.db.query(Order).order_by(desc(Order.created_at)).limit(limit).all()

    def get_order_items(self, order_id: str) -> List[OrderItem]:
        return self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

    def has_paid_purchase(self, user_id: str, product_id: str, delivered: bool = False) -> bool:
        """Backend order-data check used for review eligibility / verified badge."""
        query = (
            self.db.query(Order.id)
            .join(OrderItem)
            .filter(
                Order.user_id == user_id,
                Order.payment_status.in_(["paid", "refunded", "partially_refunded"]),
                Order.order_status.notin_(["pending", "cancelled"]),
                OrderItem.product_id == product_id,
            )
        )
        if delivered:
            query = query.filter(Order.order_status == "delivered")
        return query.first() is not None

    def create_order(
        self,
        order_in: OrderCreate,
        user_id: str,
        *,
        subtotal: Decimal,
        discount_amount: Decimal,
        tax_amount: Decimal,
        shipping_cost: Decimal,
        total_amount: Decimal,
        shipping_method: str,
        shipping_address: str,
        shipping_address_snapshot: Optional[str] = None,
        coupon_id: Optional[str] = None,
    ) -> Order:
        """Build and persist the order row (no commit — caller commits so that
        inventory reservations and order creation are atomic)."""
        db_order = Order(
            user_id=user_id,
            subtotal=subtotal,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            shipping_cost=shipping_cost,
            total_amount=total_amount,
            payment_method=order_in.payment_method,  # Stored until the demo payment settles
            shipping_method=shipping_method,
            shipping_address=shipping_address,
            shipping_address_snapshot=shipping_address_snapshot,
            coupon_id=coupon_id,
        )
        self.db.add(db_order)
        self.db.flush()
        self.db.refresh(db_order)
        return db_order

    def add_order_item(self, order_id: str, product_id: str, product_name: str, quantity: int, price: Decimal):
        item = OrderItem(
            order_id=order_id,
            product_id=product_id,
            product_name=product_name,
            quantity=quantity,
            price=price,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def update_order_status(self, order: Order, status: str) -> None:
        order.order_status = status

    def update_payment_status(self, order: Order, status: str) -> None:
        order.payment_status = status

    def set_tracking(self, order: Order, tracking_number: str) -> None:
        order.tracking_number = tracking_number

    def set_shipment_status(self, order: Order, shipment_status: str) -> None:
        order.shipment_status = shipment_status

    def add_status_history(
        self,
        order_id: str,
        from_status: Optional[str],
        to_status: str,
        changed_by: Optional[str] = None,
        note: Optional[str] = None,
    ) -> OrderStatusHistory:
        """Append an order status history row (no commit — caller commits)."""
        row = OrderStatusHistory(
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=changed_by,
            note=note,
        )
        self.db.add(row)
        return row