from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    # Column lengths: full_name VARCHAR(100), email VARCHAR(255)
    full_name: Annotated[str, Field(min_length=2, max_length=100)]
    email: Annotated[EmailStr, Field(max_length=255)]

class UserCreate(UserBase):
    # Same policy as the frontend: 8-128 characters.
    password: Annotated[str, Field(min_length=8, max_length=128)]
    # Self-registration may only grant customer/seller. Admin accounts are
    # created by scripts/seed.py or scripts/create_admin.py — never via the API
    # (prevents privilege escalation).
    role: Literal["customer", "seller"] = "customer"

class ChangePasswordRequest(BaseModel):
    current_password: Annotated[str, Field(min_length=1, max_length=128)]
    new_password: Annotated[str, Field(min_length=8, max_length=128)]

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None

class UserResponse(UserBase):
    id: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"

class AuthResponse(Token):
    user: UserResponse
