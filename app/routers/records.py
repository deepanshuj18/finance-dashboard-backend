"""Financial records routes — CRUD with role-based access."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.rbac import require_role
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.record import RecordCreate, RecordOut, RecordUpdate
from app.services.record_service import (
    create_record,
    list_records,
    soft_delete_record,
    update_record,
)

router = APIRouter(prefix="/records", tags=["Financial Records"])


@router.get(
    "/",
    summary="List and filter records (All authenticated users)",
)
async def get_records(
    type: str | None = Query(default=None, pattern="^(INCOME|EXPENSE)$"),
    category_id: int | None = None,
    category: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await list_records(
        db,
        record_type=type,
        category_id=category_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        search=search,
        page=page,
        page_size=page_size,
    )
    # Serialize items through Pydantic
    items = [RecordOut.model_validate(r) for r in result["items"]]
    return {
        "items": items,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.post(
    "/",
    response_model=RecordOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a financial record (Analyst, Admin)",
)
async def create(
    body: RecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ANALYST", "ADMIN")),
):
    record = await create_record(
        db,
        amount=body.amount,
        record_type=body.type,
        category_id=body.category_id,
        date=body.date,
        created_by=current_user.id,
        description=body.description,
    )
    return record


@router.patch(
    "/{record_id}",
    response_model=RecordOut,
    summary="Update a financial record (Analyst, Admin)",
)
async def update(
    record_id: int,
    body: RecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ANALYST", "ADMIN")),
):
    updates = body.model_dump(exclude_unset=True)
    try:
        record = await update_record(db, record_id, **updates)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return record


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft-delete a financial record (Admin only)",
)
async def delete(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    try:
        await soft_delete_record(db, record_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"detail": "Record soft-deleted successfully"}
