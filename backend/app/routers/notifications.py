from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.repositories.notification_repo import NotificationRepository
from app.schemas.notification import NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(NotificationRepository(db))


@router.get("", response_model=List[NotificationResponse])
def list_notifications(current_user: User = Depends(get_current_active_user), svc: NotificationService = Depends(get_notification_service)):
    return svc.list(current_user)


@router.get("/unread-count")
def unread_count(current_user: User = Depends(get_current_active_user), svc: NotificationService = Depends(get_notification_service)):
    return svc.unread_count(current_user)


@router.post("/mark-all-read")
def mark_all_read(current_user: User = Depends(get_current_active_user), svc: NotificationService = Depends(get_notification_service)):
    return svc.mark_all_read(current_user)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(notification_id: str, current_user: User = Depends(get_current_active_user), svc: NotificationService = Depends(get_notification_service)):
    return svc.mark_read(notification_id, current_user)
