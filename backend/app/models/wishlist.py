"""Wishlist models."""
import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Wishlist(Base):
    __tablename__ = "wishlists"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("WishlistItem", back_populates="wishlist", cascade="all, delete-orphan")


class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    wishlist_id = Column(String, ForeignKey("wishlists.id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    wishlist = relationship("Wishlist", back_populates="items")
    product = relationship("Product")

    __table_args__ = (
        # wishlist_id already indexed via index=True on the column — an explicit
        # Index with the same name causes duplicate CREATE INDEX on create_all.
        UniqueConstraint("wishlist_id", "product_id", name="uq_wishlist_product"),
    )
