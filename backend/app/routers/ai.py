from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

from app.dependencies.auth import get_current_active_user
from app.dependencies.roles import require_admin
from app.models.user import User
from app.services.ai_provider import AIProvider

router = APIRouter(prefix="/ai", tags=["ai"])


class FilterRequest(BaseModel):
    query: str


class ReviewSummaryRequest(BaseModel):
    reviews: list[dict]


class ProductDescRequest(BaseModel):
    product: dict


@router.post("/assistant/filters")
def assistant_filters(req: FilterRequest, current_user: User = Depends(get_current_active_user)):
    provider = AIProvider()
    res = provider.generate_structured_filters(req.query)
    # validate - no SQL-like keys
    forbidden = ["sql", "query", "execute", "delete", "update", "insert", "drop"]
    if any(k in str(res).lower() for k in forbidden):
        raise HTTPException(status_code=400, detail="Invalid AI output")
    return res


@router.post("/reviews/summary")
def review_summary(req: ReviewSummaryRequest, current_user: User = Depends(get_current_active_user)):
    provider = AIProvider()
    return provider.summarize_reviews(req.reviews)


@router.post("/products/description/draft", dependencies=[Depends(require_admin)])
def product_description_draft(req: ProductDescRequest, current_user: User = Depends(get_current_active_user)):
    provider = AIProvider()
    return provider.generate_product_description_draft(req.product)
