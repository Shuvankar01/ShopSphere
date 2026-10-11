from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, actor_id: str | None = None, actor_email: str | None = None,
               action: str = "", entity: str | None = None, entity_id: str | None = None,
               details: str | None = None, ip_address: str | None = None,
               user_agent: str | None = None) -> AuditLog:
        log = AuditLog(
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)
        self.db.flush()
        return log

    def list(self, limit: int = 100, offset: int = 0):
        return (self.db.query(AuditLog)
                .order_by(AuditLog.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all())

    def count(self) -> int:
        return self.db.query(AuditLog).count()
