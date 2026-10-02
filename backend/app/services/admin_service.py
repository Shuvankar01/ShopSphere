from typing import List
from app.repositories.user_repo import UserRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.order_repo import OrderRepository
from app.schemas.admin import AdminStatsResponse
from app.schemas.order import OrderResponse
from app.schemas.user import UserResponse
from app.schemas.product import ProductResponse
from app.models.user import User
from app.core.exceptions import ForbiddenException

class AdminService:
    def __init__(
        self,
        user_repo: UserRepository,
        product_repo: ProductRepository,
        order_repo: OrderRepository
    ):
        self.user_repo = user_repo
        self.product_repo = product_repo
        self.order_repo = order_repo
        
    def _check_admin(self, current_user: User):
        if current_user.role != "admin":
            raise ForbiddenException("Admin access required")

    def get_dashboard_stats(self, current_user: User) -> AdminStatsResponse:
        self._check_admin(current_user)
        
        return AdminStatsResponse(
            total_users=self.user_repo.get_total_count(),
            total_orders=self.order_repo.get_total_count(),
            total_products=self.product_repo.get_total_count(),
            revenue=self.order_repo.get_total_revenue(),
            recent_orders=[OrderResponse.model_validate(o) for o in self.order_repo.get_recent_orders()]
        )

    def get_all_users(self, current_user: User) -> List[UserResponse]:
        self._check_admin(current_user)
        return [UserResponse.model_validate(u) for u in self.user_repo.get_all()]

    def get_all_orders(self, current_user: User) -> List[OrderResponse]:
        self._check_admin(current_user)
        return [OrderResponse.model_validate(o) for o in self.order_repo.get_all_orders()]
        
    def get_all_products(self, current_user: User) -> List[ProductResponse]:
        self._check_admin(current_user)
        products, _ = self.product_repo.list_products(limit=1000) # Simple unpaginated fetch for admin table
        return [ProductResponse.model_validate(p) for p in products]
