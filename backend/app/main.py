from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.exceptions import BaseAPIException

# Database
from app.middleware.error_handler import (
    api_exception_handler,
    general_exception_handler,
)
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

# Import ALL models so SQLAlchemy registers them with Base.metadata
from app.models import (  # noqa: F401
    Address,
    AuditLog,
    Banner,
    Brand,
    Cart,
    CartItem,
    Category,
    Coupon,
    CouponUsage,
    Inventory,
    InventoryMovement,
    Notification,
    Order,
    OrderItem,
    OrderStatusHistory,
    Payment,
    PaymentTransaction,
    Product,
    ProductImage,
    ProductVariant,
    Refund,
    Return,
    ReturnItem,
    Review,
    ReviewImage,
    Role,
    User,
    UserRole,
    Wishlist,
    WishlistItem,
)

# Routers
from app.routers import (
    addresses,
    admin,
    auth,
    cart,
    coupons,
    inventory,
    orders,
    payments,
    products,
    refunds,
    returns,
    shipping,
    users,
    wishlist,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# NOTE: Tables are created by Alembic migrations.
# Do NOT call Base.metadata.create_all in production.

# CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Middlewares (added last → outermost, so security headers cover CORS responses too)
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Exception Handlers
app.add_exception_handler(BaseAPIException, api_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(addresses.router, prefix=settings.API_V1_STR)
app.include_router(products.router, prefix=settings.API_V1_STR)
app.include_router(cart.router, prefix=settings.API_V1_STR)
app.include_router(shipping.router, prefix=settings.API_V1_STR)
app.include_router(orders.router, prefix=settings.API_V1_STR)
app.include_router(payments.router, prefix=settings.API_V1_STR)
app.include_router(refunds.router, prefix=settings.API_V1_STR)
app.include_router(returns.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(inventory.router, prefix=settings.API_V1_STR)
app.include_router(wishlist.router, prefix=settings.API_V1_STR)
app.include_router(coupons.router, prefix=settings.API_V1_STR)

# Local (development) image storage: files uploaded for product images are
# served from settings.UPLOAD_DIR. Metadata lives in PostgreSQL.
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to ShopSphere API",
        "docs": "/docs",
        "openapi": f"{settings.API_V1_STR}/openapi.json",
        "environment": settings.ENVIRONMENT,
    }
