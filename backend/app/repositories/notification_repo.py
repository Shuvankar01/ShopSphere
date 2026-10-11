from typing import List

from sqlalchemy.orm import Session

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str, title: str, body: str, type_: str | None = None) -> Notification:
        n = Notification(user_id=user_id, title=title, body=body, type=type_)
        self.db.add(n)
        return n

    def list_for_user(self, user_id: str) -> List[Notification]:
        return (
            self.db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .all()
        )

    def unread_count(self, user_id: str) -> int:
        return (
            self.db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
            .count()
        )

    def mark_read(self, user_id: str, notification_id: str) -> Notification | None:
        n = (
            self.db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if n:
            n.is_read = True
            self.db.flush()
        return n

    def mark_all_read(self, user_id: str) -> int:
        updated = (
            self.db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
            .update({"is_read": True})
        )
        self.db.flush()
        return updated
