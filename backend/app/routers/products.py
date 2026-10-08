"""Products router — catalog, categories, brands, variants, images, reviews, search."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user, get_current_user_optional
from app.models.user import User
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.product import (
    BrandCreate,
    BrandResponse,
    BrandUpdate,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    PaginatedProducts,
    ProductCreate,
    ProductImageCreate,
    ProductImageResponse,
    ProductResponse,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantResponse,
    ProductVariantUpdate,
    ReviewCreate,
    ReviewResponse,
)
from app.services.product_service import ProductService

router = APIRouter(tags=["products"])


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(ProductRepository(db), InventoryRepository(db))


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(svc: ProductService = Depends(get_product_service)):
    return svc.get_categories()


@router.post("/categories", response_model=CategoryResponse, status_code=201)
def create_category(
    data: CategoryCreate,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_product_service),
):
    return svc.create_category(data, current_user)


@router.put("/categories/{cat_id}", response_model=CategoryResponse)
def update_category(
    cat_id: str,
    data: CategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_product_service),
):
    return svc.update_category(cat_id, data, current_user)


# ---------------------------------------------------------------------------
# Brands
# ---------------------------------------------------------------------------

@router.get("/brands", response_model=List[BrandResponse])
def get_brands(svc: ProductService = Depends(get_product_service)):
    return svc.get_brands()


@router.post("/brands", response_model=BrandResponse, status_code=201)
def create_brand(
    data: BrandCreate,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_product_service),
):
    return svc.create_brand(data, current_user)


@router.put("/brands/{brand_id}", response_model=BrandResponse)
def update_brand(
    brand_id: str,
    data: BrandUpdate,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_product_service),
):
    return svc.update_brand(brand_id, data, current_user)


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@router.get("/products", response_model=PaginatedProducts)
def list_products(
    q: Optional[str] = None,
    category: Optional[str] = None,
    brand_id: Optional[str] = None,
    min: Optional[float] = None,
    max: Optional[float] = None,
    min_rating: Optional[float] = None,
    in_stock: Optional[bool] = None,
    has_discount: Optional[bool] = None,
    sort: Optional[str] = "newest",
    seller_id: Optional[str] = None,
    page: int = Query(1, ge=1, description="1-based page number"),
    limit: int = Query(24, ge=1, le=100, description="Page size (1-100)"),
    include_inactive: bool = False,
    current_user: Optional[User] = Depends(get_current_user_optional),
    svc: ProductService = Depends(get_product_service),
):
    return svc.list_products(
        q=q, category=category, brand_id=brand_id,
        min_price=min, max_price=max, min_rating=min_rating,
        in_stock=in_stock, has_discount=has_discount,
        sort=sort, page=page, limit=limit, seller_id=seller_id,
        include_inactive=include_inactive, current_user=current_user,
    )


@router.get("/products/search/suggestions", response_model=List[str])
def search_suggestions(
    q: str = Query(..., min_length=2),
    svc: ProductService = Depends(get_product_service),
):
    return svc.search_suggestions(q)


@router.get("/products/{id}", response_model=ProductResponse)
def get_product(
    id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    svc: ProductService = Depends(get_product_service),
):
    return svc.get_product(id, current_user)


@router.get("/products/{id}/related", response_model=List[ProductResponse])
def get_related_products(
    id: str,
    limit: int = Query(8, ge=1, le=24),
    svc: ProductService = Depends(get_product_service),
):
    return svc.get_related_products(id, limit=limit)


@router.post("/products", response_model=ProductResponse, status_code=201)
def create_product(
    data: ProductCreate,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_product_service),
):
    return svc.create_product(data, current_user)


@router.put("/products/{id}", response_model=ProductResponse)
def update_product(
    id: str,
    data: ProductUpdate,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_product_service),
):
    return svc.update_product(id, data, current_user)


@router.delete("/products/{id}", status_code=204)
def delete_product(
    id: str,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_product_service),
):
    svc.delete_product(id, current_user)


# ---------------------------------------------------------------------------
# Product Images
# ---------------------------------------------------------------------------

@router.post("/products/{id}/images", response_model=ProductImageResponse, status_code=201)
def add_image(
    id: str,
    data: ProductImageCreate,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_product_service),
):
    return svc.add_image(id, data, current_user)


@router.post("/products/{id}/images/upload", response_model=ProductImageResponse, status_code=201)
def upload_image(
    id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_product_service),
):
    """Upload a local image file for a product (development storage)."""
    return svc.upload_image(id, file, current_user)


@router.delete("/products/{id}/images/{image_id}", status_code=204)
def delete_image(
    id: str,
    image_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_product_service),
):
    svc.delete_image(image_id, current_user)


# ---------------------------------------------------------------------------
# Product Variants
# ---------------------------------------------------------------------------

@router.post("/products/{id}/variants", response_model=ProductVariantResponse, status_code=201)
def create_variant(
    id: str,
    data: ProductVariantCreate,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_product_service),
):
    return svc.create_variant(id, data, current_user)


@router.put("/products/{id}/variants/{variant_id}", response_model=ProductVariantResponse)
def update_variant(
    id: str,
    variant_id: str,
    data: ProductVariantUpdate,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_product_service),
):
    return svc.update_variant(variant_id, data, current_user)


@router.delete("/products/{id}/variants/{variant_id}", status_code=204)
def delete_variant(
    id: str,
    variant_id: str,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_product_service),
):
    svc.delete_variant(variant_id, current_user)


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

@router.get("/products/{id}/reviews", response_model=List[ReviewResponse])
def get_reviews(id: str, svc: ProductService = Depends(get_product_service)):
    return svc.get_reviews(id)


@router.post("/products/{id}/reviews", response_model=ReviewResponse, status_code=201)
def add_review(
    id: str,
    data: ReviewCreate,
    current_user: User = Depends(get_current_active_user),
    svc: ProductService = Depends(get_product_service),
):
    return svc.add_review(id, data, current_user)
