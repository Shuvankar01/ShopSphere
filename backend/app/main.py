from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import BaseAPIException
from app.middleware.error_handler import (
    api_exception_handler,
    general_exception_handler,
)
from app.middleware.logging_middleware import LoggingMiddleware

# Database
from app.database.connection import engine
from app.models.base import Base

# Import ALL models so SQLAlchemy registers them
from app.models.user import User
from app.models.product import Product
from app.models.cart import Cart
from app.models.order import Order

# Routers
from app.routers import (
    auth,
    users,
    products,
    cart,
    orders,
    payments,
    admin,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Create database tables automatically (for SQLite development)
Base.metadata.create_all(bind=engine)

# CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Middlewares
app.add_middleware(LoggingMiddleware)

# Exception Handlers
app.add_exception_handler(BaseAPIException, api_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(products.router, prefix=settings.API_V1_STR)
app.include_router(cart.router, prefix=settings.API_V1_STR)
app.include_router(orders.router, prefix=settings.API_V1_STR)
app.include_router(payments.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to ShopSphere API",
        "docs": "/docs",
        "openapi": f"{settings.API_V1_STR}/openapi.json",
        "environment": settings.ENVIRONMENT,
    }