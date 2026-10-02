from pydantic import BaseModel
from typing import List
from app.schemas.order import OrderResponse

class AdminStatsResponse(BaseModel):
    total_users: int
    total_orders: int
    total_products: int
    revenue: float
    recent_orders: List[OrderResponse]
