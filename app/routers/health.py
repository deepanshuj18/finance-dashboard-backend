"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Basic health check")
async def health_check():
    """Return 200 OK if the API server is alive."""
    return {"status": "ok", "environment": "unknown"}


@router.get("/health/db", summary="Database health check")
async def db_health_check(db: AsyncSession = Depends(get_db)):
    """Check if the database connection is alive."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "details": str(e)}
