from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.dependencies.roles import require_admin
from app.models.user import User
from app.repositories.banner_repo import BannerRepository
from app.schemas.banner import BannerCreate, BannerResponse, BannerUpdate
from app.services.banner_service import BannerService

router = APIRouter(prefix="/banners", tags=["banners"])


def get_banner_service(db: Session = Depends(get_db)) -> BannerService:
    return BannerService(BannerRepository(db))


@router.get("", response_model=list[BannerResponse])
def list_banners(active_only: bool = Query(False), svc: BannerService = Depends(get_banner_service)):
    return svc.list(active_only=active_only)


@router.post("", response_model=BannerResponse, dependencies=[Depends(require_admin)])
def create_banner(data: BannerCreate, current_user: User = Depends(get_current_active_user),
                  svc: BannerService = Depends(get_banner_service)):
    # admin audit would be logged by caller if needed; basic
    return svc.create(data)


@router.get("/{banner_id}", response_model=BannerResponse)
def get_banner(banner_id: str, svc: BannerService = Depends(get_banner_service)):
    return svc.get(banner_id)


@router.put("/{banner_id}", response_model=BannerResponse, dependencies=[Depends(require_admin)])
def update_banner(banner_id: str, data: BannerUpdate,
                  current_user: User = Depends(get_current_active_user),
                  svc: BannerService = Depends(get_banner_service)):
    return svc.update(banner_id, data)


@router.delete("/{banner_id}", dependencies=[Depends(require_admin)])
def delete_banner(banner_id: str, current_user: User = Depends(get_current_active_user),
                  svc: BannerService = Depends(get_banner_service)):
    return svc.delete(banner_id)
