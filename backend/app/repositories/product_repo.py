from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from typing import List, Tuple
from app.models.product import Product, Category, Review
from app.schemas.product import ProductCreate, ProductUpdate, ReviewCreate

class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_categories(self) -> List[Category]:
        return self.db.query(Category).all()

    def get_product(self, id: str) -> Product | None:
        return self.db.query(Product).filter(Product.id == id).first()

    def get_total_count(self) -> int:
        return self.db.query(Product).count()

    def list_products(
        self, q: str = None, category: str = None, min_price: float = None, max_price: float = None,
        sort: str = "newest", skip: int = 0, limit: int = 24
    ) -> Tuple[List[Product], int]:
        query = self.db.query(Product)

        if q:
            query = query.filter(Product.name.ilike(f"%{q}%"))
        if category:
            query = query.filter(Product.category_id == category)
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)

        total = query.count()

        if sort == "newest":
            query = query.order_by(desc(Product.created_at))
        elif sort == "price_asc":
            query = query.order_by(asc(Product.price))
        elif sort == "price_desc":
            query = query.order_by(desc(Product.price))
        elif sort == "rating":
            query = query.order_by(desc(Product.rating))

        products = query.offset(skip).limit(limit).all()
        return products, total

    def create_product(self, product_in: ProductCreate, seller_id: str) -> Product:
        db_product = Product(
            **product_in.model_dump(),
            seller_id=seller_id
        )
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return db_product

    def update_product(self, db_product: Product, product_in: ProductUpdate) -> Product:
        update_data = product_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_product, field, value)
        self.db.commit()
        self.db.refresh(db_product)
        return db_product

    def delete_product(self, db_product: Product):
        self.db.delete(db_product)
        self.db.commit()

    def get_reviews(self, product_id: str) -> List[Review]:
        return self.db.query(Review).filter(Review.product_id == product_id).all()

    def create_review(self, review_in: ReviewCreate, product_id: str, user_id: str, user_name: str) -> Review:
        db_review = Review(
            product_id=product_id,
            user_id=user_id,
            user_name=user_name,
            **review_in.model_dump()
        )
        self.db.add(db_review)
        self.db.commit()
        self.db.refresh(db_review)
        return db_review

    def update_product_rating(self, product: Product):
        reviews = self.get_reviews(product.id)
        if reviews:
            product.review_count = len(reviews)
            product.rating = sum(r.rating for r in reviews) / product.review_count
        else:
            product.review_count = 0
            product.rating = None
        self.db.commit()
