"""Tests for dashboard analytics endpoints."""

import pytest
from httpx import AsyncClient


async def _seed_data(client: AsyncClient, admin_token: str, analyst_token: str):
    """Create categories and records for dashboard tests."""
    from tests.conftest import AsyncSessionTest
    from app.models.category import Category

    async with AsyncSessionTest() as session:
        cat1 = Category(name="Salary", description="Salaries")
        cat2 = Category(name="Rent", description="Monthly rent")
        session.add_all([cat1, cat2])
        await session.commit()
        await session.refresh(cat1)
        await session.refresh(cat2)

    records = [
        {"amount": 10000, "type": "INCOME", "category_id": cat1.id, "date": "2026-01-15T00:00:00+05:30"},
        {"amount": 8000, "type": "INCOME", "category_id": cat1.id, "date": "2026-02-15T00:00:00+05:30"},
        {"amount": 3000, "type": "EXPENSE", "category_id": cat2.id, "date": "2026-01-20T00:00:00+05:30"},
        {"amount": 3000, "type": "EXPENSE", "category_id": cat2.id, "date": "2026-02-20T00:00:00+05:30"},
        {"amount": 500, "type": "EXPENSE", "category_id": cat2.id, "date": "2026-03-05T00:00:00+05:30"},
    ]

    for rec in records:
        await client.post(
            "/api/v1/records/",
            json=rec,
            headers={"Authorization": f"Bearer {analyst_token}"},
        )


@pytest.mark.asyncio
class TestDashboardSummary:
    async def test_summary(
        self, client: AsyncClient, admin_token: str, analyst_token: str
    ):
        await _seed_data(client, admin_token, analyst_token)
        resp = await client.get(
            "/api/v1/dashboard/summary",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_income"] == 18000.0
        assert data["total_expenses"] == 6500.0
        assert data["net_balance"] == 11500.0
        assert data["record_count"] == 5

    async def test_unauthenticated_summary(self, client: AsyncClient):
        resp = await client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestDashboardByCategory:
    async def test_by_category(
        self, client: AsyncClient, admin_token: str, analyst_token: str
    ):
        await _seed_data(client, admin_token, analyst_token)
        resp = await client.get(
            "/api/v1/dashboard/by-category",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        names = [d["category_name"] for d in data]
        assert "Salary" in names
        assert "Rent" in names


@pytest.mark.asyncio
class TestDashboardTrends:
    async def test_trends_analyst_access(
        self, client: AsyncClient, admin_token: str, analyst_token: str
    ):
        await _seed_data(client, admin_token, analyst_token)
        resp = await client.get(
            "/api/v1/dashboard/trends",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2  # At least Jan & Feb

    async def test_trends_viewer_blocked(
        self, client: AsyncClient, viewer_token: str
    ):
        resp = await client.get(
            "/api/v1/dashboard/trends",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestDashboardRecent:
    async def test_recent(
        self, client: AsyncClient, admin_token: str, analyst_token: str
    ):
        await _seed_data(client, admin_token, analyst_token)
        resp = await client.get(
            "/api/v1/dashboard/recent",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 10
