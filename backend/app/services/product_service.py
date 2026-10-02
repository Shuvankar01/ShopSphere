from typing import List, Tuple
from app.repositories.product_repo import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate, ReviewCreate, PaginatedProducts, ProductResponse, CategoryResponse
from app.models.user import User
from app.core.exceptions import NotFoundException, ForbiddenException
import math

class ProductService:
    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo

    def get_categories(self) -> List[CategoryResponse]:
        categories = self.product_repo.get_categories()
        return [CategoryResponse.model_validate(c) for c in categories]

    def list_products(
        self, q: str = None, category: str = None, min_price: float = None, max_price: float = None,
        sort: str = "newest", page: int = 1, limit: int = 24
    ) -> PaginatedProducts:
        skip = (page - 1) * limit
        products, total = self.product_repo.list_products(
            q=q, category=category, min_price=min_price, max_price=max_price,
            sort=sort, skip=skip, limit=limit
        )
        return PaginatedProducts(
            items=[ProductResponse.model_validate(p) for p in products],
            total=total,
            page=page,
            limit=limit
        )

    def get_product(self, product_id: str) -> ProductResponse:
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        return ProductResponse.model_validate(product)

    def create_product(self, product_in: ProductCreate, current_user: User) -> ProductResponse:
        if current_user.role not in ["seller", "admin"]:
            raise ForbiddenException("Only sellers and admins can create products")
        product = self.product_repo.create_product(product_in, seller_id=current_user.id)
        return ProductResponse.model_validate(product)

    def update_product(self, product_id: str, product_in: ProductUpdate, current_user: User) -> ProductResponse:
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        if product.seller_id != current_user.id and current_user.role != "admin":
            raise ForbiddenException("Not authorized to update this product")
            
        updated = self.product_repo.update_product(product, product_in)
        return ProductResponse.model_validate(updated)

    def delete_product(self, product_id: str, current_user: User):
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        if product.seller_id != current_user.id and current_user.role != "admin":
            raise ForbiddenException("Not authorized to delete this product")
        self.product_repo.delete_product(product)

    def get_reviews(self, product_id: str):
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        return self.product_repo.get_reviews(product_id)

    def add_review(self, product_id: str, review_in: ReviewCreate, current_user: User):
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
            
        review = self.product_repo.create_review(
            review_in=review_in,
            product_id=product_id,
            user_id=current_user.id,
            user_name=current_user.full_name
        )
        self.product_repo.update_product_rating(product)
        return review
