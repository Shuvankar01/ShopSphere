"""Register all SQLAlchemy models so they appear in Base.metadata."""
from .base import Base
from .user import User
from .role import Role, UserRole
from .address import Address
from .product import (
    Category, Brand, Product, ProductVariant, ProductImage, Review, ReviewImage,
)
from .inventory import Inventory, InventoryMovement
from .cart import Cart, CartItem
from .order import Order, OrderItem, OrderStatusHistory
from .wishlist import Wishlist, WishlistItem
from .payment import Payment, PaymentTransaction, Refund
from .coupon import Coupon, CouponUsage
from .return_request import Return, ReturnItem
from .notification import Notification
from .banner import Banner
from .audit import AuditLog

__all__ = [
    "Base",
    "User",
    "Role",
    "UserRole",
    "Address",
    "Category",
    "Brand",
    "Product",
    "ProductVariant",
    "ProductImage",
    "Review",
    "ReviewImage",
    "Inventory",
    "InventoryMovement",
    "Cart",
    "CartItem",
    "Order",
    "OrderItem",
    "OrderStatusHistory",
    "Wishlist",
    "WishlistItem",
    "Payment",
    "PaymentTransaction",
    "Refund",
    "Coupon",
    "CouponUsage",
    "Return",
    "ReturnItem",
    "Notification",
    "Banner",
    "AuditLog",
]
