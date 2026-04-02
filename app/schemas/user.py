"""User request/response schemas — never expose password_hash."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=4, max_length=128)
    full_name: str | None = Field(default=None, max_length=200)
    role: str = Field(default="VIEWER", pattern="^(VIEWER|ANALYST|ADMIN)$")


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None


class UserOut(BaseModel):
    id: int
    email: str
    username: str
    full_name: str | None
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(VIEWER|ANALYST|ADMIN)$")


class StatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(ACTIVE|INACTIVE)$")
