"""User notifications (foundation for order/promo notifications)."""
import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False, default="system")  # order / promo / system
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    link = Column(String(1000), nullable=True)  # in-app route, e.g. /orders/<id>
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
    )
