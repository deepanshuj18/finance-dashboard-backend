"""FastAPI application — lifespan, routers, middleware, exception handlers."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.database import engine
from app.exceptions.handlers import register_exception_handlers
from app.middleware.rate_limit import limiter
from app.models.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup (dev convenience)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Finance Dashboard API",
    description=(
        "A production-quality async backend for a finance dashboard — "
        "JWT auth, RBAC, financial records CRUD with soft delete, "
        "and aggregation analytics."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── Rate limiter ───────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Exception handlers ─────────────────────────────────────────
register_exception_handlers(app)

from fastapi.middleware.gzip import GZipMiddleware
from app.middleware.logging import StructuredLoggingMiddleware
from app.routers import auth, dashboard, records, users, health

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(StructuredLoggingMiddleware)

# ── Routers ────────────────────────────────────────────────────
app.include_router(health.router)

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(auth.router)
api_v1.include_router(users.router)
api_v1.include_router(records.router)
api_v1.include_router(dashboard.router)

app.include_router(api_v1)

