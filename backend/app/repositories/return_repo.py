"""Return (RMA) repository."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.return_request import Return, ReturnItem


class ReturnRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, return_id: str) -> Optional[Return]:
        return self.db.query(Return).filter(Return.id == return_id).first()

    def get_user_returns(self, user_id: str) -> List[Return]:
        return (
            self.db.query(Return)
            .filter(Return.user_id == user_id)
            .order_by(Return.created_at.desc())
            .all()
        )

    def get_returns_for_order(self, order_id: str) -> List[Return]:
        return (
            self.db.query(Return)
            .filter(Return.order_id == order_id)
            .order_by(Return.created_at.desc())
            .all()
        )

    def get_all(self) -> List[Return]:
        return self.db.query(Return).order_by(Return.created_at.desc()).all()

    def create(self, user_id: str, order_id: str, reason: str) -> Return:
        ret = Return(user_id=user_id, order_id=order_id, reason=reason)
        self.db.add(ret)
        self.db.flush()
        return ret

    def add_item(
        self, return_id: str, order_item_id: str, quantity: int, reason: Optional[str]
    ) -> ReturnItem:
        item = ReturnItem(return_id=return_id, order_item_id=order_item_id, quantity=quantity, reason=reason)
        self.db.add(item)
        self.db.flush()
        return item

    def returned_quantity(self, order_item_id: str) -> int:
        """Already-requested quantity for an order line (rejected/cancelled
        returns are ignored so the item can be requested again)."""
        from sqlalchemy import func
        from sqlalchemy.sql import select

        total = (
            self.db.execute(
                select(func.coalesce(func.sum(ReturnItem.quantity), 0)).where(
                    ReturnItem.order_item_id == order_item_id,
                    ReturnItem.return_request.has(
                        Return.status.in_(["requested", "approved", "received", "completed"])
                    ),
                )
            )
            .scalar()
        )
        return int(total or 0)

    def set_status(self, ret: Return, status: str) -> None:
        ret.status = status