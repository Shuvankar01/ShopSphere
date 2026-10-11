from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.roles import require_admin
from app.repositories.audit_repo import AuditLogRepository
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/admin", tags=["admin"])


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    return AuditService(AuditLogRepository(db))


@router.get("/audit-logs", response_model=list[AuditLogResponse], dependencies=[Depends(require_admin)])
def list_audit_logs(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                    svc: AuditService = Depends(get_audit_service)):
    return svc.list(limit=limit, offset=offset)
