from typing import List
from app.repositories.order_repo import OrderRepository
from app.repositories.cart_repo import CartRepository
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from app.models.user import User
from app.core.exceptions import NotFoundException, BadRequestException, ForbiddenException

class OrderService:
    def __init__(self, order_repo: OrderRepository, cart_repo: CartRepository):
        self.order_repo = order_repo
        self.cart_repo = cart_repo

    def create_order(self, order_in: OrderCreate, current_user: User) -> OrderResponse:
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        self.cart_repo.calculate_subtotal(cart)
        
        if not cart.items:
            raise BadRequestException("Cart is empty")
            
        order = self.order_repo.create_order(order_in, current_user.id, cart.subtotal)
        
        for item in cart.items:
            price = item.product.discount_price if item.product.discount_price is not None else item.product.price
            self.order_repo.add_order_item(
                order_id=order.id,
                product_id=item.product.id,
                product_name=item.product.name,
                quantity=item.quantity,
                price=price
            )
            # Optional: Deduct stock from product_repo here
            
        self.cart_repo.clear_cart(cart)
        return OrderResponse.model_validate(order)

    def get_user_orders(self, current_user: User) -> List[OrderResponse]:
        orders = self.order_repo.get_user_orders(current_user.id)
        return [OrderResponse.model_validate(o) for o in orders]

    def get_order(self, order_id: str, current_user: User) -> OrderResponse:
        order = self.order_repo.get_order(order_id)
        if not order:
            raise NotFoundException("Order not found")
            
        if order.user_id != current_user.id and current_user.role != "admin":
            raise ForbiddenException("Not authorized to view this order")
            
        return OrderResponse.model_validate(order)

    def update_order_status(self, order_id: str, status_update: OrderStatusUpdate, current_user: User) -> OrderResponse:
        if current_user.role not in ["seller", "admin"]:
            raise ForbiddenException("Not authorized to update orders")
            
        order = self.order_repo.get_order(order_id)
        if not order:
            raise NotFoundException("Order not found")
            
        self.order_repo.update_order_status(order, status_update.status)
        return OrderResponse.model_validate(order)
