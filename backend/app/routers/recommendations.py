from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_recs(db: Session = Depends(get_db)) -> RecommendationService:
    return RecommendationService(db)


@router.get("")
def recommendations(user_id: str | None = Query(None), product_id: str | None = Query(None),
                   limit: int = Query(10, ge=1, le=50), svc: RecommendationService = Depends(get_recs)):
    return {"results": svc.get_recommendations(user_id=user_id, product_id=product_id, limit=limit)}
