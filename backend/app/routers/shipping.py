"""Demo shipping router — local mock methods, no carrier APIs."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter

from app.schemas.shipping import ShippingMethodResponse
from app.services import shipping

router = APIRouter(prefix="/shipping", tags=["shipping"])


@router.get("/methods", response_model=List[ShippingMethodResponse])
def list_shipping_methods():
    """Demo delivery options with charge + estimated delivery. No external
    carrier is ever called; tracking numbers are mock/demo."""
    return shipping.get_shipping_methods()