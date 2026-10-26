"""Append-only audit log (foundation for traceability of sensitive actions).

This is the single canonical mapping of the `audit_logs` table. A second,
near-duplicate `AuditLog` class used to live in `app/models/audit_log.py`;
having two classes mapped to the same `__tablename__` merged their column sets
into one `Table` object via `extend_existing`, which silently drifted away from
the Alembic schema (the runtime SELECT referenced columns the migration never
created). Keep exactly one definition here and keep it in sync with the
migration.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_action_created", "action", "created_at"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    # NULL actor = system
    actor_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    # Denormalized actor snapshot, so the log stays readable even if the user
    # row is later removed or renamed.
    actor_id = Column(String, nullable=True)
    actor_email = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False)  # e.g. auth.login, product.update
    entity_type = Column(String(100), nullable=True)  # e.g. user, order
    entity = Column(String(100), nullable=True)
    entity_id = Column(String(100), nullable=True)
    detail = Column(Text, nullable=True)  # JSON string; never contains secrets
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    actor = relationship("User")
