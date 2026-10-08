"""Wishlist repository."""
from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session, joinedload

from app.models.wishlist import Wishlist, WishlistItem


class WishlistRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user(self, user_id: str) -> Wishlist:
        wishlist = (
            self.db.query(Wishlist)
            .options(joinedload(Wishlist.items).joinedload(WishlistItem.product))
            .filter(Wishlist.user_id == user_id)
            .first()
        )
        if not wishlist:
            wishlist = Wishlist(user_id=user_id)
            self.db.add(wishlist)
            self.db.commit()
            self.db.refresh(wishlist)
        return wishlist

    def get_item(self, wishlist_id: str, product_id: str) -> Optional[WishlistItem]:
        return (
            self.db.query(WishlistItem)
            .filter(WishlistItem.wishlist_id == wishlist_id, WishlistItem.product_id == product_id)
            .first()
        )

    def add_item(self, wishlist_id: str, product_id: str) -> WishlistItem:
        item = WishlistItem(wishlist_id=wishlist_id, product_id=product_id)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def remove_item(self, item: WishlistItem) -> None:
        self.db.delete(item)
        self.db.commit()
