from pydantic import BaseModel, ConfigDict
from typing import List
from app.schemas.product import ProductResponse

class CartItemAdd(BaseModel):
    product_id: str
    quantity: int

class CartItemUpdate(BaseModel):
    product_id: str
    quantity: int

class CartItemResponse(BaseModel):
    id: str
    product_id: str
    product: ProductResponse
    quantity: int

    model_config = ConfigDict(from_attributes=True)

class CartResponse(BaseModel):
    id: str
    user_id: str
    items: List[CartItemResponse]
    subtotal: float

    model_config = ConfigDict(from_attributes=True)
