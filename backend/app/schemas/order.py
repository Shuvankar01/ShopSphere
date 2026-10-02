from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class OrderCreate(BaseModel):
    shipping_address: str
    payment_method: str

class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    quantity: int
    price: float

    model_config = ConfigDict(from_attributes=True)

class OrderResponse(BaseModel):
    id: str
    user_id: str
    items: List[OrderItemResponse]
    total_amount: float
    order_status: str
    payment_status: str
    shipping_address: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OrderStatusUpdate(BaseModel):
    status: str
