"""Customer address-book schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AddressCreate(BaseModel):
    label: str = Field(default="home", max_length=50)
    recipient_name: str = Field(min_length=2, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=30)
    line1: str = Field(min_length=2, max_length=255)
    line2: Optional[str] = Field(default=None, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    postal_code: str = Field(min_length=2, max_length=20)
    country: str = Field(min_length=2, max_length=100)
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: Optional[str] = Field(default=None, max_length=50)
    recipient_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=30)
    line1: Optional[str] = Field(default=None, min_length=2, max_length=255)
    line2: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, min_length=2, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, min_length=2, max_length=20)
    country: Optional[str] = Field(default=None, min_length=2, max_length=100)
    is_default: Optional[bool] = None


class AddressResponse(BaseModel):
    id: str
    user_id: str
    label: str
    recipient_name: str
    phone: Optional[str] = None
    line1: str
    line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DefaultAddressRequest(BaseModel):
    address_id: str