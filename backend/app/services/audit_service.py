from app.repositories.audit_repo import AuditLogRepository
from app.models.user import User
from app.schemas.audit import AuditLogResponse


class AuditService:
    def __init__(self, audit_repo: AuditLogRepository):
        self.audit_repo = audit_repo

    def create(self, *, actor: User | None = None, action: str, entity: str | None = None,
               entity_id: str | None = None, details: str | None = None,
               ip_address: str | None = None, user_agent: str | None = None) -> None:
        actor_id = actor.id if actor else None
        actor_email = actor.email if actor else None
        self.audit_repo.create(
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.audit_repo.db.commit()

    def list(self, limit: int = 100, offset: int = 0) -> list[AuditLogResponse]:
        return [AuditLogResponse.model_validate(a) for a in self.audit_repo.list(limit=limit, offset=offset)]

    def count(self) -> int:
        return self.audit_repo.count()
