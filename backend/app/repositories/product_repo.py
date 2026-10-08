"""Product repository — all DB operations for products, categories, brands, reviews, images, variants."""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import asc, case, desc, or_
from sqlalchemy.orm import Session, joinedload

from app.models.product import (
    Brand,
    Category,
    Product,
    ProductImage,
    ProductVariant,
    Review,
)
from app.schemas.product import (
    BrandCreate,
    BrandUpdate,
    CategoryCreate,
    CategoryUpdate,
    ProductCreate,
    ProductImageCreate,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantUpdate,
    ReviewCreate,
)


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    def get_categories(self, include_inactive: bool = False) -> List[Category]:
        q = self.db.query(Category)
        if not include_inactive:
            q = q.filter(Category.is_active == True)
        return q.order_by(Category.name).all()

    def get_category(self, category_id: str) -> Optional[Category]:
        return self.db.query(Category).filter(Category.id == category_id).first()

    def get_category_by_name(self, name: str) -> Optional[Category]:
        return self.db.query(Category).filter(Category.name == name).first()

    def get_category_descendant_ids(self, category_id: str) -> List[str]:
        """All ids in the category's subtree (the category itself first), for
        hierarchical filtering."""
        ids: List[str] = [category_id]
        frontier = [category_id]
        while frontier:
            nxt = (
                self.db.query(Category.id)
                .filter(Category.parent_id.in_(frontier))
                .all()
            )
            frontier = [row[0] for row in nxt]
            ids.extend(frontier)
        return ids

    def create_category(self, data: CategoryCreate) -> Category:
        cat = Category(**data.model_dump())
        self.db.add(cat)
        self.db.commit()
        self.db.refresh(cat)
        return cat

    def update_category(self, cat: Category, data: CategoryUpdate) -> Category:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(cat, field, value)
        self.db.commit()
        self.db.refresh(cat)
        return cat

    # ------------------------------------------------------------------
    # Brands
    # ------------------------------------------------------------------

    def get_brands(self, include_inactive: bool = False) -> List[Brand]:
        q = self.db.query(Brand)
        if not include_inactive:
            q = q.filter(Brand.is_active == True)
        return q.order_by(Brand.name).all()

    def get_brand(self, brand_id: str) -> Optional[Brand]:
        return self.db.query(Brand).filter(Brand.id == brand_id).first()

    def get_brand_by_name(self, name: str) -> Optional[Brand]:
        return self.db.query(Brand).filter(Brand.name == name).first()

    def create_brand(self, data: BrandCreate) -> Brand:
        brand = Brand(**data.model_dump())
        self.db.add(brand)
        self.db.commit()
        self.db.refresh(brand)
        return brand

    def update_brand(self, brand: Brand, data: BrandUpdate) -> Brand:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(brand, field, value)
        self.db.commit()
        self.db.refresh(brand)
        return brand

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    def get_product(self, product_id: str) -> Optional[Product]:
        return (
            self.db.query(Product)
            .options(
                joinedload(Product.category),
                joinedload(Product.brand),
                joinedload(Product.images),
                joinedload(Product.variants),
            )
            .filter(Product.id == product_id)
            .first()
        )

    def get_total_count(self) -> int:
        return self.db.query(Product).count()

    def list_products(
        self,
        q: Optional[str] = None,
        category: Optional[str] = None,
        brand_id: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        min_rating: Optional[float] = None,
        in_stock: Optional[bool] = None,
        has_discount: Optional[bool] = None,
        sort: str = "newest",
        skip: int = 0,
        limit: int = 24,
        seller_id: Optional[str] = None,
        include_inactive: bool = False,
    ) -> Tuple[List[Product], int]:
        query = (
            self.db.query(Product)
            .options(joinedload(Product.category), joinedload(Product.brand))
        )

        if not include_inactive:
            query = query.filter(Product.is_active == True)
        if q:
            query = query.filter(
                or_(
                    Product.name.ilike(f"%{q}%"),
                    Product.description.ilike(f"%{q}%"),
                    Product.sku.ilike(f"%{q}%"),
                )
            )
        if category:
            # Category filter includes every descendant of the chosen category.
            cat_ids = self.get_category_descendant_ids(category)
            query = query.filter(Product.category_id.in_(cat_ids))
        if brand_id:
            query = query.filter(Product.brand_id == brand_id)
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        if min_rating is not None:
            query = query.filter(Product.rating >= min_rating)
        if in_stock is True:
            query = query.filter(Product.stock > 0)
        if has_discount is True:
            query = query.filter(Product.discount_price != None)
        if seller_id:
            query = query.filter(Product.seller_id == seller_id)

        total = query.count()

        if sort == "newest":
            query = query.order_by(desc(Product.created_at))
        elif sort == "price_asc":
            query = query.order_by(asc(Product.price))
        elif sort == "price_desc":
            query = query.order_by(desc(Product.price))
        elif sort == "rating":
            query = query.order_by(desc(Product.rating).nullslast())
        elif sort == "popularity":
            query = query.order_by(desc(Product.review_count), desc(Product.created_at))

        products = query.offset(skip).limit(limit).all()
        return products, total

    def create_product(self, data: ProductCreate, seller_id: str) -> Product:
        payload = data.model_dump()
        product = Product(**payload, seller_id=seller_id)
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update_product(self, product: Product, data: ProductUpdate) -> Product:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        self.db.commit()
        self.db.refresh(product)
        return product

    def delete_product(self, product: Product) -> None:
        # Soft deactivation: products are referenced by order_items/reviews and
        # historical records must survive. The row is kept, just hidden.
        product.is_active = False
        self.db.commit()
        self.db.refresh(product)

    def search_suggestions(self, q: str, limit: int = 10) -> List[str]:
        results = (
            self.db.query(Product.name)
            .filter(Product.name.ilike(f"%{q}%"), Product.is_active == True)
            .limit(limit)
            .all()
        )
        return [r[0] for r in results]

    def get_related_products(self, product: Product, limit: int = 8) -> List[Product]:
        """Active products in the same category, same-brand items first."""
        return (
            self.db.query(Product)
            .options(joinedload(Product.category), joinedload(Product.brand))
            .filter(
                Product.is_active == True,
                Product.id != product.id,
                Product.category_id == product.category_id,
            )
            .order_by(
                case((Product.brand_id == product.brand_id, 0), else_=1),
                desc(Product.review_count),
                desc(Product.created_at),
            )
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------
    # Product Images
    # ------------------------------------------------------------------

    def add_image(self, product_id: str, data: ProductImageCreate) -> ProductImage:
        img = ProductImage(product_id=product_id, **data.model_dump())
        self.db.add(img)
        self.db.commit()
        self.db.refresh(img)
        return img

    def delete_image(self, image: ProductImage) -> None:
        self.db.delete(image)
        self.db.commit()

    def get_image(self, image_id: str) -> Optional[ProductImage]:
        return self.db.query(ProductImage).filter(ProductImage.id == image_id).first()

    # ------------------------------------------------------------------
    # Product Variants
    # ------------------------------------------------------------------

    def create_variant(self, product_id: str, data: ProductVariantCreate) -> ProductVariant:
        variant = ProductVariant(product_id=product_id, **data.model_dump())
        self.db.add(variant)
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def update_variant(self, variant: ProductVariant, data: ProductVariantUpdate) -> ProductVariant:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(variant, field, value)
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def get_variant(self, variant_id: str) -> Optional[ProductVariant]:
        return self.db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()

    def delete_variant(self, variant: ProductVariant) -> None:
        self.db.delete(variant)
        self.db.commit()

    # ------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------

    def get_reviews(self, product_id: str) -> List[Review]:
        return (
            self.db.query(Review)
            .filter(Review.product_id == product_id)
            .order_by(desc(Review.created_at))
            .all()
        )

    def get_review_by_user_product(self, user_id: str, product_id: str) -> Optional[Review]:
        return (
            self.db.query(Review)
            .filter(Review.user_id == user_id, Review.product_id == product_id)
            .first()
        )

    def create_review(
        self, data: ReviewCreate, product_id: str, user_id: str, user_name: str
    ) -> Review:
        review = Review(
            product_id=product_id,
            user_id=user_id,
            user_name=user_name,
            **data.model_dump(),
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def update_product_rating(self, product: Product) -> None:
        reviews = self.get_reviews(product.id)
        if reviews:
            product.review_count = len(reviews)
            product.rating = round(
                sum(r.rating for r in reviews) / len(reviews), 2
            )
        else:
            product.review_count = 0
            product.rating = None
        self.db.commit()
