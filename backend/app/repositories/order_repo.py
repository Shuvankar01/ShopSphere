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

    def create_order(
        self,
        order_in: OrderCreate,
        user_id: str,
        total_amount: Decimal,
        coupon_id: Optional[str] = None,
        discount_amount: Decimal = Decimal("0.00"),
    ) -> Order:
        """Build and persist the order row (no commit — caller commits so that
        inventory reservations and order creation are atomic)."""
        db_order = Order(
            user_id=user_id,
            shipping_address=order_in.shipping_address,
            payment_method=order_in.payment_method, # Stored temporarily until payment service processes
            total_amount=total_amount,
            coupon_id=coupon_id,
            discount_amount=discount_amount,
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
            price=price
        )
        self.db.add(item)
        self.db.flush()
        return item

    def update_order_status(self, order: Order, status: str):
        order.order_status = status
        self.db.commit()
        self.db.refresh(order)

    def update_payment_status(self, order: Order, status: str):
        order.payment_status = status
        self.db.commit()
        self.db.refresh(order)

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
