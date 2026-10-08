"""Append-only audit log (foundation for traceability of sensitive actions)."""
import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    # NULL actor = system
    actor_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False)  # e.g. auth.login, product.update
    entity_type = Column(String(100), nullable=False)  # e.g. user, order
    entity_id = Column(String(100), nullable=True)
    detail = Column(Text, nullable=True)  # JSON string; never contains secrets
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    actor = relationship("User")

    __table_args__ = (
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )
