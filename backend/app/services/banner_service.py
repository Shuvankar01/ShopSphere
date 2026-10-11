from app.core.exceptions import NotFoundException
from app.repositories.banner_repo import BannerRepository
from app.schemas.banner import BannerCreate, BannerResponse, BannerUpdate


class BannerService:
    def __init__(self, banner_repo: BannerRepository):
        self.banner_repo = banner_repo

    def list(self, active_only: bool = False) -> list[BannerResponse]:
        return [BannerResponse.model_validate(b) for b in self.banner_repo.list(active_only=active_only)]

    def get(self, banner_id: str) -> BannerResponse:
        b = self.banner_repo.get(banner_id)
        if not b:
            raise NotFoundException("Banner not found")
        return BannerResponse.model_validate(b)

    def create(self, data: BannerCreate) -> BannerResponse:
        b = self.banner_repo.create(**data.model_dump())
        self.banner_repo.db.commit()
        return BannerResponse.model_validate(b)

    def update(self, banner_id: str, data: BannerUpdate) -> BannerResponse:
        b = self.banner_repo.get(banner_id)
        if not b:
            raise NotFoundException("Banner not found")
        self.banner_repo.update(b, **data.model_dump(exclude_unset=True))
        self.banner_repo.db.commit()
        return BannerResponse.model_validate(b)

    def delete(self, banner_id: str) -> dict:
        b = self.banner_repo.get(banner_id)
        if not b:
            raise NotFoundException("Banner not found")
        self.banner_repo.delete(b)
        self.banner_repo.db.commit()
        return {"message": "Banner deleted"}
