from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, PaginatedProducts, ReviewCreate, ReviewResponse, CategoryResponse
from app.services.product_service import ProductService
from app.repositories.product_repo import ProductRepository
from app.database.session import get_db
from app.dependencies.auth import get_current_active_user, get_current_user
from app.models.user import User

router = APIRouter(tags=["products"])

def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(ProductRepository(db))

@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(product_service: ProductService = Depends(get_product_service)):
    return product_service.get_categories()

@router.get("/products", response_model=PaginatedProducts)
def list_products(
    q: Optional[str] = None,
    category: Optional[str] = None,
    min: Optional[float] = None,
    max: Optional[float] = None,
    sort: Optional[str] = "newest",
    page: Optional[int] = 1,
    limit: Optional[int] = 24,
    product_service: ProductService = Depends(get_product_service)
):
    return product_service.list_products(
        q=q, category=category, min_price=min, max_price=max,
        sort=sort, page=page, limit=limit
    )

@router.get("/products/{id}", response_model=ProductResponse)
def get_product(id: str, product_service: ProductService = Depends(get_product_service)):
    return product_service.get_product(id)

@router.post("/products", response_model=ProductResponse)
def create_product(
    product_in: ProductCreate,
    current_user: User = Depends(get_current_active_user),
    product_service: ProductService = Depends(get_product_service)
):
    return product_service.create_product(product_in, current_user)

@router.put("/products/{id}", response_model=ProductResponse)
def update_product(
    id: str,
    product_in: ProductUpdate,
    current_user: User = Depends(get_current_active_user),
    product_service: ProductService = Depends(get_product_service)
):
    return product_service.update_product(id, product_in, current_user)

@router.delete("/products/{id}", status_code=204)
def delete_product(
    id: str,
    current_user: User = Depends(get_current_active_user),
    product_service: ProductService = Depends(get_product_service)
):
    product_service.delete_product(id, current_user)

@router.get("/products/{id}/reviews", response_model=List[ReviewResponse])
def get_reviews(id: str, product_service: ProductService = Depends(get_product_service)):
    return product_service.get_reviews(id)

@router.post("/products/{id}/reviews", response_model=ReviewResponse)
def add_review(
    id: str,
    review_in: ReviewCreate,
    current_user: User = Depends(get_current_active_user),
    product_service: ProductService = Depends(get_product_service)
):
    return product_service.add_review(id, review_in, current_user)
