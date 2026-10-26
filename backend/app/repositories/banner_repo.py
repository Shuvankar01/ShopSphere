from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session
from app.models.banner import Banner


class BannerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, banner_id: str) -> Banner | None:
        return self.db.query(Banner).filter(Banner.id == banner_id).first()

    def list(self, active_only: bool = False) -> List[Banner]:
        q = self.db.query(Banner)
        now = datetime.now(timezone.utc)
        if active_only:
            q = q.filter(Banner.is_active == True)
            q = q.filter((Banner.starts_at == None) | (Banner.starts_at <= now))
            q = q.filter((Banner.ends_at == None) | (Banner.ends_at >= now))
        return q.order_by(Banner.created_at.desc()).all()

    def all(self) -> List[Banner]:
        return self.db.query(Banner).order_by(Banner.created_at.desc()).all()

    def create(self, **data) -> Banner:
        b = Banner(**data)
        self.db.add(b)
        self.db.flush()
        return b

    def update(self, banner: Banner, **data) -> Banner:
        for k, v in data.items():
            if hasattr(banner, k):
                setattr(banner, k, v)
        self.db.flush()
        return banner

    def delete(self, banner: Banner) -> None:
        self.db.delete(banner)
