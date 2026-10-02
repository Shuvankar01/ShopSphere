from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryResponse(CategoryBase):
    id: str

    model_config = ConfigDict(from_attributes=True)

class ProductBase(BaseModel):
    name: str
    description: str
    price: float
    discount_price: Optional[float] = None
    stock: int
    image_url: Optional[str] = None
    category_id: str

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    discount_price: Optional[float] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None
    category_id: Optional[str] = None

class ProductResponse(ProductBase):
    id: str
    seller_id: str
    created_at: datetime
    rating: Optional[float] = None
    review_count: Optional[int] = 0
    category: Optional[CategoryResponse] = None

    model_config = ConfigDict(from_attributes=True)

class PaginatedProducts(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    limit: int

class ReviewBase(BaseModel):
    rating: int
    comment: str

class ReviewCreate(ReviewBase):
    pass

class ReviewResponse(ReviewBase):
    id: str
    user_id: str
    user_name: str
    product_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
