# Finance Dashboard API

A production-quality async FastAPI backend for a finance dashboard with JWT authentication, role-based access control, financial records management, and aggregation analytics.

## Architecture

```
HTTP Request → Rate Limiter → JWT Auth → RBAC Guard → Router → Service → SQLAlchemy → PostgreSQL
```

**Key design decisions:**

| Decision | Choice | Why |
|---|---|---|
| Async | `asyncpg` + `AsyncSession` | Non-blocking I/O for parallel dashboard queries |
| RBAC | `Depends(require_role())` | One-line, declarative, testable permissions |
| Service layer | Zero FastAPI imports | Business logic testable without HTTP server |
| Schemas | Split `*Create` / `*Update` / `*Out` | Never expose `password_hash` or `deleted_at` |
| Soft delete | `deleted_at` column | Audit-friendly — data is never actually gone |
| Dashboard | `func.sum`, `case()`, `extract()` | Type-checked aggregations, no raw SQL |

## Tech Stack

- **Framework:** FastAPI (async)
- **Database:** PostgreSQL + asyncpg
- **ORM:** SQLAlchemy 2.0 (async)
- **Auth:** JWT via python-jose + passlib/bcrypt
- **Migrations:** Alembic (async)
- **Rate limiting:** slowapi
- **Tests:** pytest + pytest-asyncio + httpx

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL running locally

### Setup

```bash
# Clone and enter
cd finance_backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Create the database
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE finance_db;"

# Configure .env (already has sensible defaults)
# Edit .env if your PostgreSQL credentials differ

# Start the server
uvicorn app.main:app --reload
```

The server starts at `http://127.0.0.1:8000`. Tables are auto-created on first startup.

### API Docs
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

## API Endpoints

| Method | Path | Role | Description |
|--------|------|------|-------------|
| `POST` | `/auth/register` | Public | Create account (returns JWT) |
| `POST` | `/auth/login` | Public | Authenticate (returns JWT) |
| `GET` | `/users` | ADMIN | List all users |
| `POST` | `/users` | ADMIN | Create user with role |
| `PATCH` | `/users/{id}/role` | ADMIN | Change user role |
| `PATCH` | `/users/{id}/status` | ADMIN | Activate / deactivate |
| `GET` | `/records` | ALL | List + filter + paginate |
| `POST` | `/records` | ANALYST, ADMIN | Create financial record |
| `PATCH` | `/records/{id}` | ANALYST, ADMIN | Update record |
| `DELETE` | `/records/{id}` | ADMIN | Soft delete |
| `GET` | `/dashboard/summary` | ALL | Income, expenses, net |
| `GET` | `/dashboard/by-category` | ALL | Category breakdown |
| `GET` | `/dashboard/trends` | ANALYST, ADMIN | Monthly trend data |
| `GET` | `/dashboard/recent` | ALL | Last 10 transactions |

## Roles

| Role | View Dashboard | View Records | Create/Edit Records | Delete Records | Manage Users |
|------|:-:|:-:|:-:|:-:|:-:|
| **VIEWER** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **ANALYST** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **ADMIN** | ✅ | ✅ | ✅ | ✅ | ✅ |

## Project Structure

```
finance_backend/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, router registration
│   ├── config.py                # pydantic-settings (.env loader)
│   ├── database.py              # Async engine + session factory
│   ├── middleware/
│   │   ├── auth.py              # JWT decode → returns current user
│   │   └── rate_limit.py        # slowapi 100 req/min per IP
│   ├── dependencies/
│   │   └── rbac.py              # require_role() factory
│   ├── models/                  # SQLAlchemy ORM
│   │   ├── base.py              # DeclarativeBase, TimestampMixin
│   │   ├── user.py              # User, Role enum, Status enum
│   │   ├── record.py            # FinancialRecord, soft delete
│   │   ├── category.py          # Category
│   │   └── audit_log.py         # AuditLog
│   ├── schemas/                 # Pydantic v2 (request + response)
│   │   ├── auth.py              # Register, Login, Token
│   │   ├── user.py              # UserCreate, UserOut, RoleUpdate
│   │   ├── record.py            # RecordCreate, RecordOut, RecordFilter
│   │   └── dashboard.py         # SummaryOut, TrendOut, CategoryBreakdown
│   ├── routers/                 # Thin route handlers
│   │   ├── auth.py, users.py, records.py, dashboard.py
│   ├── services/                # Business logic (zero FastAPI imports)
│   │   ├── auth_service.py, user_service.py, record_service.py, dashboard_service.py
│   └── exceptions/
│       └── handlers.py          # Global error handlers (400/401/422/500)
├── alembic/                     # Database migrations
├── tests/
│   ├── conftest.py              # Shared fixtures, test DB
│   ├── test_auth.py
│   ├── test_records.py
│   └── test_dashboard.py
├── .env
├── alembic.ini
├── requirements.txt
└── README.md
```

## Running Tests

Tests use SQLite in-memory — no PostgreSQL needed for testing.

```bash
pip install aiosqlite   # Required only for tests
python -m pytest tests/ -v
```

## Running E2E Test Scenarios 
To test all roles, endpoints, features, and calculate exactly matching aggregations locally, simply execute the custom test script:
```bash
python seed_and_test.py
```

## Advanced Database Performance (Current & Future)
The system currently leverages standard enterprise deployment paradigms suitable for medium-to-large traffic:
1. **Partial Indexes:** PostgreSQL `Index` with `postgresql_where=text("deleted_at IS NULL")` explicitly guarantees soft-deleted items never bloat B-Tree branches.
2. **Composite Grouping:** `(category_id, type, date)` heavily optimizes Dashboard Aggregate Grouping.
3. **Eager Loading Constraints:** Implemented `selectinload` globally preventing catastrophic N+1 Relationship Loading delays.
4. **Asynchronous Connection Pooling:** Advanced tuning natively supports high throughput via explicit Postgres connection pool limits.

### Future Scalability Improvements
For hyperscaling applications serving tens of thousands of active concurrent requests, here are immediate recommendations:
- **Cursor-Based Pagination:** The current implementation uses simple offset pagination. For immensely large datasets crossing millions of rows, keyset cursor pagination can be integrated sequentially.
- **Materialized Redis Caching:** Dashboard summary outputs generate complex queries. By integrating `redis.setex("dashboard:summary:123", 300, json.dumps(summary))`, these high-read computations can be instantly shifted to in-memory TTL serving (e.g. 5 minutes cache) circumventing the relational database.
- **Query Profiling:** Any backend bottleneck diagnosis should begin using native PostgreSQL `EXPLAIN ANALYZE` to pinpoint any sub-sequential data scanning behavior across large analytics periods.

## Data Model

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│    users     │     │ financial_records │     │  categories  │
├──────────────┤     ├──────────────────┤     ├──────────────┤
│ id           │◄────│ created_by (FK)  │     │ id           │
│ email        │     │ id               │     │ name         │
│ username     │     │ amount           │     │ description  │
│ password_hash│     │ type (ENUM)      │     │ created_at   │
│ full_name    │     │ category_id (FK) │────►│ updated_at   │
│ role (ENUM)  │     │ date             │     └──────────────┘
│ status (ENUM)│     │ description      │
│ created_at   │     │ deleted_at       │     ┌──────────────┐
│ updated_at   │     │ created_at       │     │  audit_logs  │
└──────────────┘     │ updated_at       │     ├──────────────┤
                     └──────────────────┘     │ id           │
                                              │ user_id (FK) │
                                              │ action       │
                                              │ entity       │
                                              │ entity_id    │
                                              │ details      │
                                              │ created_at   │
                                              └──────────────┘
```

## Assumptions & Tradeoffs

1. **Auto-create tables on startup** — convenient for development; in production, use Alembic migrations exclusively.
2. **New users default to VIEWER role** — safest default; admins can promote via `PATCH /users/{id}/role`.
3. **Soft delete only on financial records** — auditors need data trails; other entities use hard delete.
4. **No refresh token endpoint** — keeps auth simple; add token refresh for long-lived sessions.
5. **Category management** — categories are seeded via DB or admin tools; no CRUD endpoint to keep scope focused on core requirements.

## License

MIT
