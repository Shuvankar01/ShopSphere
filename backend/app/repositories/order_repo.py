from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from app.models.order import Order, OrderItem
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
        
    def get_total_revenue(self) -> float:
        from sqlalchemy.sql import func
        total = self.db.query(func.sum(Order.total_amount)).filter(Order.payment_status == 'paid').scalar()
        return total or 0.0

    def get_recent_orders(self, limit: int = 5) -> List[Order]:
        return self.db.query(Order).order_by(desc(Order.created_at)).limit(limit).all()

    def create_order(self, order_in: OrderCreate, user_id: str, total_amount: float) -> Order:
        db_order = Order(
            user_id=user_id,
            shipping_address=order_in.shipping_address,
            payment_method=order_in.payment_method, # Stored temporarily until payment service processes
            total_amount=total_amount
        )
        self.db.add(db_order)
        self.db.commit()
        self.db.refresh(db_order)
        return db_order

    def add_order_item(self, order_id: str, product_id: str, product_name: str, quantity: int, price: float):
        item = OrderItem(
            order_id=order_id,
            product_id=product_id,
            product_name=product_name,
            quantity=quantity,
            price=price
        )
        self.db.add(item)
        self.db.commit()

    def update_order_status(self, order: Order, status: str):
        order.order_status = status
        self.db.commit()
        self.db.refresh(order)
        
    def update_payment_status(self, order: Order, status: str):
        order.payment_status = status
        self.db.commit()
        self.db.refresh(order)
