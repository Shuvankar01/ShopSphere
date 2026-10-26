from typing import List
from app.repositories.user_repo import UserRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.order_repo import OrderRepository
from app.schemas.admin import AdminStatsResponse
from app.schemas.order import OrderResponse
from app.schemas.user import UserResponse
from app.schemas.product import ProductResponse, ProductUpdate
from app.models.user import User
from app.core.exceptions import ForbiddenException, NotFoundException
from app.dependencies.roles import collect_role_names

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
        # `UserRole.role` is a relationship to a `Role` row, so the name has to
        # be read from `r.role.name` — stringifying the relationship object
        # yields its repr, which never matches a role name.
        if "admin" not in collect_role_names(current_user):
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

    def toggle_user_status(self, user_id: str, current_user: User) -> UserResponse:
        """Activate / deactivate a user. Deactivating keeps the row so orders,
        reviews and audit history stay intact."""
        self._check_admin(current_user)
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        user.is_active = not user.is_active
        self.user_repo.db.commit()
        self.user_repo.db.refresh(user)
        return UserResponse.model_validate(user)

    def toggle_product_status(self, product_id: str, current_user: User) -> ProductResponse:
        """Activate / deactivate a product (soft delete — the row survives)."""
        self._check_admin(current_user)
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
        updated = self.product_repo.update_product(
            product, ProductUpdate(is_active=not product.is_active)
        )
        return ProductResponse.model_validate(updated)
