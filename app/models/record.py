"""FinancialRecord ORM model with soft delete support."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RecordType(str, enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class FinancialRecord(TimestampMixin, Base):
    __tablename__ = "financial_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[RecordType] = mapped_column(
        Enum(RecordType, name="record_type_enum", create_constraint=True),
        nullable=False,
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=False
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    __table_args__ = (
        # 1. Partial indexes on active records
        Index(
            "idx_active_records_date",
            "date",
            postgresql_where=text("deleted_at IS NULL")
        ),
        Index(
            "idx_active_records_type",
            "type",
            postgresql_where=text("deleted_at IS NULL")
        ),
        Index(
            "idx_active_records_category_id",
            "category_id",
            postgresql_where=text("deleted_at IS NULL")
        ),
        # 2. Composite indexes for common filters
        Index(
            "idx_type_date_active",
            "type",
            "date",
            postgresql_where=text("deleted_at IS NULL")
        ),
        Index(
            "idx_category_date_active",
            "category_id",
            "date",
            postgresql_where=text("deleted_at IS NULL")
        ),
        # 3. Index for dashboard summary queries
        Index(
            "idx_dashboard_grouping",
            "category_id",
            "type",
            "date",
            postgresql_where=text("deleted_at IS NULL")
        ),
    )

    # Relationships
    category = relationship("Category", lazy="selectin")
    creator = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<FinancialRecord id={self.id} type={self.type} amount={self.amount}>"
