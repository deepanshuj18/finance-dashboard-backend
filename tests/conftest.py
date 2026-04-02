"""Shared test fixtures — SQLite test database + test client + auth helpers."""

import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base

# Use a file-based SQLite for tests — avoids connection sharing issues
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test.db")
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)
AsyncSessionTest = async_sessionmaker(
    bind=engine_test, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionTest() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test, drop after."""
    # Import all models so Base.metadata knows about them
    from app.models import audit_log, category, record, user  # noqa: F401

    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    # Clean up the test DB file
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass


@pytest_asyncio.fixture
async def client():
    """Async test client with DB override — bypasses lifespan."""
    from app.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    """Register a user and promote to ADMIN, return token."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@test.com",
            "username": "admin",
            "password": "admin123",
            "full_name": "Admin User",
        },
    )
    assert resp.status_code == 201, f"Register failed: {resp.text}"

    # Promote to admin directly via DB
    async with AsyncSessionTest() as session:
        from sqlalchemy import update
        from app.models.user import Role, User

        await session.execute(
            update(User).where(User.email == "admin@test.com").values(role=Role.ADMIN)
        )
        await session.commit()

    # Re-login to get token with admin role
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "admin123"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def analyst_token(client: AsyncClient, admin_token: str) -> str:
    """Create an analyst user via admin, return token."""
    resp = await client.post(
        "/api/v1/users/",
        json={
            "email": "analyst@test.com",
            "username": "analyst",
            "password": "analyst123",
            "full_name": "Analyst User",
            "role": "ANALYST",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, f"Create analyst failed: {resp.text}"

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@test.com", "password": "analyst123"},
    )
    assert resp.status_code == 200, f"Analyst login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def viewer_token(client: AsyncClient) -> str:
    """Register a viewer user, return token."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "viewer@test.com",
            "username": "viewer",
            "password": "viewer123",
        },
    )
    assert resp.status_code == 201, f"Register viewer failed: {resp.text}"
    return resp.json()["access_token"]
