from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.product import Product
from app.models.order import Order, OrderItem


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db

    def get_recommendations(self, user_id: str | None = None, product_id: str | None = None,
                           limit: int = 10) -> List[Dict[str, Any]]:
        # Simple rule-based: same category if product given, else popular from purchases
        products = []
        if product_id:
            p = self.db.query(Product).filter(Product.id == product_id).first()
            if p and p.category_id:
                products = self.db.query(Product).filter(
                    Product.category_id == p.category_id,
                    Product.id != p.id,
                    Product.is_active == True
                ).limit(limit).all()
        if not products and user_id:
            # based on purchase history
            ordered = self.db.query(Product).join(OrderItem).join(Order).filter(
                Order.user_id == user_id
            ).distinct().limit(limit * 2).all()
            products = list(ordered)[:limit]
        if not products:
            products = self.db.query(Product).filter(Product.is_active == True).order_by(Product.created_at.desc()).limit(limit).all()
        return [{"id": pr.id, "name": pr.name, "price": float(pr.price), "category_id": pr.category_id} for pr in products]
