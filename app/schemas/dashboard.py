"""Dashboard summary response schemas."""

from pydantic import BaseModel


class SummaryOut(BaseModel):
    total_income: float
    total_expenses: float
    net_balance: float
    record_count: int


class CategoryBreakdown(BaseModel):
    category_id: int
    category_name: str
    total_income: float
    total_expenses: float
    net: float
    count: int


class TrendOut(BaseModel):
    year: int
    month: int
    total_income: float
    total_expenses: float
    net: float


class RecentRecordOut(BaseModel):
    id: int
    amount: float
    type: str
    category_name: str
    date: str
    description: str | None
