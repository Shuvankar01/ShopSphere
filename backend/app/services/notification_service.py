from typing import List

from app.models.user import User
from app.repositories.notification_repo import NotificationRepository
from app.schemas.notification import NotificationResponse


class NotificationService:
    def __init__(self, notification_repo: NotificationRepository):
        self.notification_repo = notification_repo

    def list(self, current_user: User) -> List[NotificationResponse]:
        return [
            NotificationResponse.model_validate(n)
            for n in self.notification_repo.list_for_user(current_user.id)
        ]

    def unread_count(self, current_user: User) -> dict:
        return {"count": self.notification_repo.unread_count(current_user.id)}

    def mark_read(self, notification_id: str, current_user: User) -> NotificationResponse:
        from app.core.exceptions import NotFoundException

        n = self.notification_repo.mark_read(current_user.id, notification_id)
        if not n:
            raise NotFoundException("Notification not found")
        return NotificationResponse.model_validate(n)

    def mark_all_read(self, current_user: User) -> dict:
        count = self.notification_repo.mark_all_read(current_user.id)
        self.notification_repo.db.commit()
        return {"updated": count}
