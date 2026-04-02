"""Dashboard routes — aggregation endpoints for the frontend."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.rbac import require_role
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.dashboard import CategoryBreakdown, RecentRecordOut, SummaryOut, TrendOut
from app.services.dashboard_service import (
    get_by_category,
    get_recent,
    get_summary,
    get_trends,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard Analytics"])


@router.get(
    "/summary",
    response_model=SummaryOut,
    summary="Total income, expenses, net balance (All authenticated users)",
)
async def summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_summary(db)


@router.get(
    "/by-category",
    response_model=list[CategoryBreakdown],
    summary="Income/expense breakdown by category (All authenticated users)",
)
async def by_category(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_by_category(db)


@router.get(
    "/trends",
    response_model=list[TrendOut],
    summary="Monthly income/expense trends (Analyst, Admin)",
)
async def trends(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ANALYST", "ADMIN")),
):
    return await get_trends(db)


@router.get(
    "/recent",
    response_model=list[RecentRecordOut],
    summary="Last 10 transactions (All authenticated users)",
)
async def recent(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_recent(db)
