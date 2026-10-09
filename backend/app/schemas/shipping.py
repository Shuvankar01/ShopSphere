"""Demo shipping methods — no external carrier APIs. Methods are defined by the
local demo shipping service (see app.services.shipping)."""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class ShippingMethodResponse(BaseModel):
    code: str
    name: str
    charge: Decimal
    estimated_days_min: int
    estimated_days_max: int
    description: str