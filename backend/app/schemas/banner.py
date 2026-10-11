from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BannerCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    image_url: Optional[str] = Field(default=None, max_length=2000)
    link_url: Optional[str] = Field(default=None, max_length=2000)
    is_active: bool = True
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class BannerUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    image_url: Optional[str] = Field(default=None, max_length=2000)
    link_url: Optional[str] = Field(default=None, max_length=2000)
    is_active: Optional[bool] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class BannerResponse(BaseModel):
    id: str
    title: str
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    is_active: bool
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_currently_active: bool

    model_config = ConfigDict(from_attributes=True)
