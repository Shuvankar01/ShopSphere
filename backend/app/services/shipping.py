"""Demo shipping — a local, credential-free implementation.

No Shiprocket / Delhivery / Blue Dart or any real carrier API is ever called.
Methods are static demo data with charges and mock estimated-delivery windows;
tracking numbers are generated locally when an order ships.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Dict, Optional

from app.core.exceptions import BadRequestException
from app.schemas.shipping import ShippingMethodResponse

DEFAULT_SHIPPING_METHOD = "standard"

# code -> demo shipping method definition.
_SHIPPING_METHODS: Dict[str, dict] = {
    "standard": {
        "code": "standard",
        "name": "Standard Delivery",
        "charge": Decimal("39.00"),
        "estimated_days_min": 4,
        "estimated_days_max": 7,
        "description": "Delivered in 4–7 business days",
    },
    "express": {
        "code": "express",
        "name": "Express Delivery",
        "charge": Decimal("89.00"),
        "estimated_days_min": 1,
        "estimated_days_max": 2,
        "description": "Delivered in 1–2 business days",
    },
    "priority": {
        "code": "priority",
        "name": "Priority Delivery",
        "charge": Decimal("149.00"),
        "estimated_days_min": 0,
        "estimated_days_max": 1,
        "description": "Next business day delivery",
    },
}


def get_shipping_methods() -> list[ShippingMethodResponse]:
    return [ShippingMethodResponse(**m) for m in _SHIPPING_METHODS.values()]


def get_shipping_method(code: str) -> Optional[dict]:
    return _SHIPPING_METHODS.get(code)


def require_shipping_method(code: str) -> dict:
    method = _SHIPPING_METHODS.get(code)
    if not method:
        raise BadRequestException(f"Unknown shipping method '{code}'")
    return method


def charge_for(code: str) -> Decimal:
    return require_shipping_method(code)["charge"]


def estimate_delivery(code: str) -> str:
    method = require_shipping_method(code)
    if method["estimated_days_min"] == 0:
        return "Next business day"
    return (
        f"{method['estimated_days_min']}–{method['estimated_days_max']} business days"
    )


def generate_tracking_number(order_id: str) -> str:
    """Mock tracking number: DEMO + short order id + random suffix."""
    return f"DEMO{order_id[:8].upper()}{uuid.uuid4().hex[:6].upper()}"