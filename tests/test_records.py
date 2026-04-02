"""Tests for financial records — CRUD, RBAC enforcement, filtering, soft delete."""

import pytest
from httpx import AsyncClient


async def _create_category(client: AsyncClient, admin_token: str) -> int:
    """Helper: seed a category directly via DB since there's no category endpoint."""
    from tests.conftest import AsyncSessionTest
    from app.models.category import Category

    async with AsyncSessionTest() as session:
        cat = Category(name="Salary", description="Monthly salary")
        session.add(cat)
        await session.commit()
        await session.refresh(cat)
        return cat.id


@pytest.mark.asyncio
class TestRecordCRUD:
    async def test_create_record_as_analyst(
        self, client: AsyncClient, analyst_token: str, admin_token: str
    ):
        cat_id = await _create_category(client, admin_token)
        resp = await client.post(
            "/api/v1/records/",
            json={
                "amount": 5000.00,
                "type": "INCOME",
                "category_id": cat_id,
                "date": "2026-03-15T00:00:00+05:30",
                "description": "March salary",
            },
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["amount"] == 5000.00
        assert data["type"] == "INCOME"

    async def test_viewer_cannot_create_record(
        self, client: AsyncClient, viewer_token: str
    ):
        resp = await client.post(
            "/api/v1/records/",
            json={
                "amount": 100,
                "type": "EXPENSE",
                "category_id": 1,
                "date": "2026-03-15T00:00:00+05:30",
            },
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    async def test_list_records(
        self, client: AsyncClient, analyst_token: str, admin_token: str
    ):
        cat_id = await _create_category(client, admin_token)
        # Create a record first
        await client.post(
            "/api/v1/records/",
            json={
                "amount": 1000,
                "type": "EXPENSE",
                "category_id": cat_id,
                "date": "2026-03-10T00:00:00+05:30",
                "description": "Office supplies",
            },
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        resp = await client.get(
            "/api/v1/records/",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 1

    async def test_unauthenticated_access(self, client: AsyncClient):
        resp = await client.get("/api/v1/records/")
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestSoftDelete:
    async def test_admin_can_soft_delete(
        self, client: AsyncClient, admin_token: str, analyst_token: str
    ):
        cat_id = await _create_category(client, admin_token)
        # Create a record
        create_resp = await client.post(
            "/api/v1/records/",
            json={
                "amount": 200,
                "type": "EXPENSE",
                "category_id": cat_id,
                "date": "2026-03-12T00:00:00+05:30",
            },
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        record_id = create_resp.json()["id"]

        # Delete it
        del_resp = await client.delete(
            f"/api/v1/records/{record_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert del_resp.status_code == 200

    async def test_analyst_cannot_delete(
        self, client: AsyncClient, analyst_token: str, admin_token: str
    ):
        cat_id = await _create_category(client, admin_token)
        create_resp = await client.post(
            "/api/v1/records/",
            json={
                "amount": 300,
                "type": "INCOME",
                "category_id": cat_id,
                "date": "2026-03-14T00:00:00+05:30",
            },
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        record_id = create_resp.json()["id"]

        del_resp = await client.delete(
            f"/api/v1/records/{record_id}",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert del_resp.status_code == 403
