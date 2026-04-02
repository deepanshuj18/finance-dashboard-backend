"""Financial record request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Must be a positive number")
    type: str = Field(..., pattern="^(INCOME|EXPENSE)$")
    category_id: int
    date: datetime
    description: str | None = Field(default=None, max_length=500)


class RecordUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    type: str | None = Field(default=None, pattern="^(INCOME|EXPENSE)$")
    category_id: int | None = None
    date: datetime | None = None
    description: str | None = Field(default=None, max_length=500)


class CategoryOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class RecordOut(BaseModel):
    id: int
    amount: float
    type: str
    category: CategoryOut
    date: datetime
    description: str | None
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecordFilter(BaseModel):
    type: str | None = Field(default=None, pattern="^(INCOME|EXPENSE)$")
    category_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    search: str | None = Field(default=None, max_length=200)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
