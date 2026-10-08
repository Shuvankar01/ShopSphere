from decimal import Decimal
from typing import List

from pydantic import BaseModel

from app.schemas.order import OrderResponse


class AdminStatsResponse(BaseModel):
    total_users: int
    total_orders: int
    total_products: int
    revenue: Decimal
    recent_orders: List[OrderResponse]
