"""Dashboard analytics service — aggregated queries using SQLAlchemy func.

Zero FastAPI imports. All aggregations use func.sum, case(), groupBy — no raw SQL.
"""

from sqlalchemy import case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.record import FinancialRecord, RecordType


async def get_summary(db: AsyncSession) -> dict:
    """
    Return total income, total expenses, net balance, and record count.
    Only considers non-deleted records.
    """
    result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (FinancialRecord.type == RecordType.INCOME, FinancialRecord.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("total_income"),
            func.coalesce(
                func.sum(
                    case(
                        (FinancialRecord.type == RecordType.EXPENSE, FinancialRecord.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("total_expenses"),
            func.count(FinancialRecord.id).label("record_count"),
        ).where(FinancialRecord.deleted_at.is_(None))
    )
    row = result.one()
    total_income = float(row.total_income)
    total_expenses = float(row.total_expenses)
    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_balance": total_income - total_expenses,
        "record_count": row.record_count,
    }


async def get_by_category(db: AsyncSession) -> list[dict]:
    """Return income/expense breakdown grouped by category."""
    result = await db.execute(
        select(
            Category.id.label("category_id"),
            Category.name.label("category_name"),
            func.coalesce(
                func.sum(
                    case(
                        (FinancialRecord.type == RecordType.INCOME, FinancialRecord.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("total_income"),
            func.coalesce(
                func.sum(
                    case(
                        (FinancialRecord.type == RecordType.EXPENSE, FinancialRecord.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("total_expenses"),
            func.count(FinancialRecord.id).label("count"),
        )
        .join(Category, FinancialRecord.category_id == Category.id)
        .where(FinancialRecord.deleted_at.is_(None))
        .group_by(Category.id, Category.name)
        .order_by(Category.name)
    )
    rows = result.all()
    return [
        {
            "category_id": row.category_id,
            "category_name": row.category_name,
            "total_income": float(row.total_income),
            "total_expenses": float(row.total_expenses),
            "net": float(row.total_income) - float(row.total_expenses),
            "count": row.count,
        }
        for row in rows
    ]


async def get_trends(db: AsyncSession) -> list[dict]:
    """Monthly income/expense trends, ordered chronologically."""
    result = await db.execute(
        select(
            extract("year", FinancialRecord.date).label("year"),
            extract("month", FinancialRecord.date).label("month"),
            func.coalesce(
                func.sum(
                    case(
                        (FinancialRecord.type == RecordType.INCOME, FinancialRecord.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("total_income"),
            func.coalesce(
                func.sum(
                    case(
                        (FinancialRecord.type == RecordType.EXPENSE, FinancialRecord.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("total_expenses"),
        )
        .where(FinancialRecord.deleted_at.is_(None))
        .group_by("year", "month")
        .order_by("year", "month")
    )
    rows = result.all()
    return [
        {
            "year": int(row.year),
            "month": int(row.month),
            "total_income": float(row.total_income),
            "total_expenses": float(row.total_expenses),
            "net": float(row.total_income) - float(row.total_expenses),
        }
        for row in rows
    ]


async def get_recent(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Return the N most recent non-deleted records."""
    result = await db.execute(
        select(FinancialRecord)
        .join(Category, FinancialRecord.category_id == Category.id)
        .where(FinancialRecord.deleted_at.is_(None))
        .order_by(FinancialRecord.date.desc())
        .limit(limit)
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "amount": r.amount,
            "type": r.type.value,
            "category_name": r.category.name if r.category else "Unknown",
            "date": r.date.isoformat(),
            "description": r.description,
        }
        for r in records
    ]
