from app.repositories.cart_repo import CartRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.cart import CartResponse
from app.models.user import User
from app.core.exceptions import NotFoundException, BadRequestException

class CartService:
    def __init__(self, cart_repo: CartRepository, product_repo: ProductRepository):
        self.cart_repo = cart_repo
        self.product_repo = product_repo

    def get_cart(self, current_user: User) -> CartResponse:
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        self.cart_repo.calculate_subtotal(cart)
        return CartResponse.model_validate(cart)

    def add_item(self, product_id: str, quantity: int, current_user: User) -> CartResponse:
        if quantity <= 0:
            raise BadRequestException("Quantity must be greater than 0")
            
        product = self.product_repo.get_product(product_id)
        if not product:
            raise NotFoundException("Product not found")
            
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        item = self.cart_repo.get_cart_item(cart.id, product_id)
        
        if item:
            self.cart_repo.update_item_quantity(item, item.quantity + quantity)
        else:
            self.cart_repo.add_item(cart.id, product_id, quantity)
            
        self.cart_repo.calculate_subtotal(cart)
        return CartResponse.model_validate(cart)

    def update_item(self, product_id: str, quantity: int, current_user: User) -> CartResponse:
        if quantity <= 0:
            return self.remove_item(product_id, current_user)
            
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        item = self.cart_repo.get_cart_item(cart.id, product_id)
        
        if not item:
            raise NotFoundException("Product not in cart")
            
        self.cart_repo.update_item_quantity(item, quantity)
        self.cart_repo.calculate_subtotal(cart)
        return CartResponse.model_validate(cart)

    def remove_item(self, product_id: str, current_user: User) -> CartResponse:
        cart = self.cart_repo.get_cart_by_user(current_user.id)
        item = self.cart_repo.get_cart_item(cart.id, product_id)
        
        if item:
            self.cart_repo.remove_item(item)
            self.cart_repo.calculate_subtotal(cart)
            
        return CartResponse.model_validate(cart)
