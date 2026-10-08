"""Product domain models: Category, Brand, Product, ProductVariant, ProductImage, Review."""
import uuid
from decimal import Decimal
from sqlalchemy import (
    Column, String, Integer, ForeignKey, Text, DateTime, Numeric,
    Boolean, UniqueConstraint, CheckConstraint, Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    parent_id = Column(String, ForeignKey("categories.id"), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # self-referential hierarchy
    parent = relationship("Category", remote_side="Category.id", back_populates="children")
    children = relationship("Category", back_populates="parent")
    products = relationship("Product", back_populates="category")

    __table_args__ = (
        CheckConstraint("id != parent_id", name="ck_category_no_self_parent"),
    )


class Brand(Base):
    __tablename__ = "brands"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(1000), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("Product", back_populates="brand")


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    sku = Column(String(100), nullable=True, unique=True, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    discount_price = Column(Numeric(10, 2), nullable=True)
    stock = Column(Integer, nullable=False, default=0)
    image_url = Column(String(1000), nullable=True)
    specifications = Column(Text, nullable=True)         # JSON string of key/value specs
    rating = Column(Numeric(3, 2), nullable=True)
    review_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    category_id = Column(String, ForeignKey("categories.id"), nullable=False, index=True)
    brand_id = Column(String, ForeignKey("brands.id"), nullable=True, index=True)
    seller_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    category = relationship("Category", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.sort_order")
    inventory = relationship("Inventory", back_populates="product", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("price > 0", name="ck_product_price_positive"),
        CheckConstraint("discount_price IS NULL OR discount_price < price", name="ck_product_discount_lt_price"),
        CheckConstraint("stock >= 0", name="ck_product_stock_nonneg"),
        # category_id / seller_id already indexed via index=True on the columns —
        # redeclaring them as explicit Index objects causes duplicate CREATE INDEX.
        Index("ix_products_is_active", "is_active"),
        # Filter/sort support (matching the Part 2 migration).
        Index("ix_products_rating", "rating"),
        Index("ix_products_discount_price", "discount_price"),
        # PostgreSQL trigram GIN indexes make '%term%' ILIKE search fast.
        # Requires the pg_trgm extension (created in the migration and in the
        # test conftest before Base.metadata.create_all).
        Index(
            "ix_products_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "ix_products_description_trgm",
            "description",
            postgresql_using="gin",
            postgresql_ops={"description": "gin_trgm_ops"},
        ),
    )


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    sku = Column(String(100), nullable=False, unique=True)
    name = Column(String(200), nullable=False)          # e.g. "Red / XL"
    price_override = Column(Numeric(10, 2), nullable=True)  # None = use product price
    stock = Column(Integer, nullable=False, default=0)
    attributes = Column(Text, nullable=True)            # JSON string: {"color":"Red","size":"XL"}
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="variants")

    __table_args__ = (
        CheckConstraint("stock >= 0", name="ck_variant_stock_nonneg"),
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    url = Column(String(1000), nullable=False)
    alt_text = Column(String(500), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="images")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    user_name = Column(String(100), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="reviews")
    images = relationship("ReviewImage", back_populates="review", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_one_review_per_user_product"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
    )


class ReviewImage(Base):
    __tablename__ = "review_images"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    review_id = Column(String, ForeignKey("reviews.id"), nullable=False, index=True)
    url = Column(String(1000), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    review = relationship("Review", back_populates="images")
