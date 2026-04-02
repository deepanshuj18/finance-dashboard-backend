"""Financial record service — CRUD, filtering, pagination, soft delete.

Zero FastAPI imports. Type-checked SQLAlchemy queries, no raw SQL.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.record import FinancialRecord, RecordType
from app.models.audit_log import AuditLog


async def create_record(
    db: AsyncSession,
    amount: float,
    record_type: str,
    category_id: int,
    date: datetime,
    created_by: int,
    description: str | None = None,
) -> FinancialRecord:
    """Create a new financial record."""
    record = FinancialRecord(
        amount=amount,
        type=RecordType(record_type),
        category_id=category_id,
        date=date,
        created_by=created_by,
        description=description,
    )
    db.add(record)
    await db.flush()
    
    # Re-fetch the fully loaded object to prevent Pydantic MissingGreenletError
    result = await db.execute(
        select(FinancialRecord)
        .options(selectinload(FinancialRecord.category), selectinload(FinancialRecord.creator))
        .where(FinancialRecord.id == record.id)
    )
    return result.scalar_one()


async def list_records(
    db: AsyncSession,
    *,
    record_type: str | None = None,
    category_id: int | None = None,
    category: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    List records with optional filtering, search, and pagination.
    Returns dict with 'items', 'total', 'page', 'page_size'.
    """
    query = select(FinancialRecord).where(FinancialRecord.deleted_at.is_(None))

    from app.models.category import Category

    # Apply filters
    if record_type:
        query = query.where(FinancialRecord.type == RecordType(record_type))
    if category_id:
        query = query.where(FinancialRecord.category_id == category_id)
    if category:
        query = query.join(FinancialRecord.category).where(Category.name.ilike(f"%{category}%"))
    if start_date:
        query = query.where(FinancialRecord.date >= start_date)
    if end_date:
        query = query.where(FinancialRecord.date <= end_date)
    if search:
        query = query.where(
            FinancialRecord.description.ilike(f"%{search}%")
        )

    # Count total matching records
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = (
        query.options(selectinload(FinancialRecord.category))
        .order_by(FinancialRecord.date.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    items = list(result.scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_record_by_id(
    db: AsyncSession, record_id: int
) -> FinancialRecord | None:
    """Fetch a single non-deleted record by ID."""
    result = await db.execute(
        select(FinancialRecord)
        .where(FinancialRecord.id == record_id)
        .where(FinancialRecord.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def update_record(
    db: AsyncSession,
    record_id: int,
    **updates,
) -> FinancialRecord:
    """Update a financial record. Raises ValueError if not found."""
    record = await get_record_by_id(db, record_id)
    if record is None:
        raise ValueError("Record not found")

    for key, value in updates.items():
        if value is not None:
            if key == "type":
                value = RecordType(value)
            setattr(record, key, value)

    await db.flush()
    
    # Re-fetch the fully loaded object to prevent Pydantic MissingGreenletError
    result = await db.execute(
        select(FinancialRecord)
        .options(selectinload(FinancialRecord.category), selectinload(FinancialRecord.creator))
        .where(FinancialRecord.id == record_id)
    )
    return result.scalar_one()


async def soft_delete_record(db: AsyncSession, record_id: int, performer_id: int) -> FinancialRecord:
    """Soft delete — sets deleted_at timestamp. Raises ValueError if not found."""
    record = await get_record_by_id(db, record_id)
    if record is None:
        raise ValueError("Record not found")

    record.deleted_at = datetime.now(timezone.utc)
    
    # Audit trail
    db.add(AuditLog(
        user_id=performer_id,
        action="SOFT_DELETE",
        entity="FinancialRecord",
        entity_id=record.id,
        details=f"Record '{record.description}' softly deleted"
    ))

    await db.flush()
    await db.refresh(record)
    return record
