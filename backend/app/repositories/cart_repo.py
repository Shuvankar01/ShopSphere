from sqlalchemy.orm import Session
from app.models.cart import Cart, CartItem
from app.models.product import Product

class CartRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_cart_by_user(self, user_id: str) -> Cart:
        cart = self.db.query(Cart).filter(Cart.user_id == user_id).first()
        if not cart:
            cart = Cart(user_id=user_id)
            self.db.add(cart)
            self.db.commit()
            self.db.refresh(cart)
        return cart

    def get_cart_item(self, cart_id: str, product_id: str) -> CartItem | None:
        return self.db.query(CartItem).filter(
            CartItem.cart_id == cart_id,
            CartItem.product_id == product_id
        ).first()

    def add_item(self, cart_id: str, product_id: str, quantity: int) -> CartItem:
        item = CartItem(cart_id=cart_id, product_id=product_id, quantity=quantity)
        self.db.add(item)
        self.db.commit()
        return item

    def update_item_quantity(self, item: CartItem, quantity: int):
        item.quantity = quantity
        self.db.commit()
        self.db.refresh(item)

    def remove_item(self, item: CartItem):
        self.db.delete(item)
        self.db.commit()

    def calculate_subtotal(self, cart: Cart):
        total = 0.0
        for item in cart.items:
            price = item.product.discount_price if item.product.discount_price is not None else item.product.price
            total += price * item.quantity
        cart.subtotal = total
        self.db.commit()

    def clear_cart(self, cart: Cart):
        for item in cart.items:
            self.db.delete(item)
        cart.subtotal = 0.0
        self.db.commit()
