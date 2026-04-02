# Design Decisions & Architectural Rationale

This document serves as a comprehensive breakdown for code reviewers, detailing **why** specific architectural patterns, libraries, and design paradigms were chosen for this Finance Dashboard Backend at every step of development.

---

## 1. Core Framework Decisions

### Why FastAPI over Django/Flask?
- **Asynchronous by Default:** Finance dashboards involve heavy I/O operations (fetching massive aggregations from databases). FastAPI's native support for Python `async/await` allows the server to handle thousands of concurrent requests dynamically.
- **Pydantic Validation:** Moving data boundary validation into strict `Pydantic v2` schemas prevents malicious injections and malformed data from ever reaching the service layer.

### Why Clean Architecture (Service Layer Separation)?
- We explicitly separated HTTP Routers (`app/routers/`) from Business Logic (`app/services/`). 
- **Rationale:** If we ever switch to GraphQL, gRPC, or run a CLI worker instance, the underlying financial math and database operations (`app/services/`) remain 100% untouched. Routers only handle HTTP mapping.

---

## 2. Database & ORM Choices

### Why PostgreSQL + `asyncpg`?
- **Hyperscaling Constraint:** Standard `psycopg2` is synchronous, meaning every DB query locks a thread until it resolves. `asyncpg` is entirely event-loop driven, yielding the thread during wait times, yielding massive concurrency improvements.
- **JSON & Aggregation:** Postgres natively handles massive grouping functions and advanced Indexing.

### Why SQLAlchemy 2.0?
- SQLAlchemy 2.0 treats async operations as first-class citizens. We utilized highly-optimized `select()` commands instead of raw strings, bringing Pythonic type-safety to our queries.

---

## 3. Data Integrity & Indexing Strategy

### Why implement "Soft Deletes" (`deleted_at`)?
- In financial systems, permanently erasing data (`DELETE FROM ...`) breaks historical auditing compliance. 
- **Rationale:** We added a `deleted_at` timestamp. Filtering `where(deleted_at.is_(None))` maintains the exact dashboard totals up to date, while keeping the digital footprint alive for administrators to review.

### Why Partial B-Tree Indexes?
Instead of creating standard Indexes across the `FinancialRecord` columns, we created **Partial Indexes** (e.g. `postgresql_where=text("deleted_at IS NULL")`). 
- **Rationale:** Because 99% of user requests ignore deleted records, a partial index forces Postgres to only construct a fast B-Tree over *active* rows. This dramatically shrinks RAM requirements and halves lookup latency.

---

## 4. Security & Access Control

### Why Stateless JWT Auth over Session Cookies?
- **Horizontal Scaling:** Instead of querying a Session Database table (which introduces an extreme bottleneck on every single API request), JWTs are verified using a highly secure mathematical cryptographic signature (`python-jose`). The server can scale to 500 instances, and every instance can independently verify the signature instantly.

### Why the `Depends(require_role())` Dependency?
- This is a declarative RBAC (Role-Based Access Control) pattern.
- **Rationale:** By putting `@router.get(..., dependencies=[Depends(require_role("ADMIN"))])` at the top of the route, the HTTP request is explicitly rejected *before* any core application logic operates. It isolates security context from business context.

---

## 5. Performance Polish

### Why compute aggregations in SQL (`func.sum()`) instead of Python?
- A standard developer might download 50,000 user rows into Python, iterate through them in a `for` loop, and sum the amounts. 
- **Rationale:** Python is inherently slower at mathematical grouping than C-compiled PostgreSQL engines. Utilizing native SQL aggregations (`func.sum`, `group_by`) pushes the heavy lifting to the DB, meaning the backend only transports ~0.5KB of structured JSON back to the client instead of megabytes of raw arrays.

### Why apply global Exception Catchers?
- As demonstrated when trying to insert a missing Foreign Key (Category 0), the database throws native `sqlalchemy.exc.IntegrityError` responses.
- **Rationale:** We attached global traps in `app/exceptions/handlers.py` to seamlessly convert cryptic crashes into clean APIs: `409 Conflict` (for foreign key breaks) and `422 Unprocessable Entity` (for invalid types). This prevents internal server mechanics from leaking to potential attackers.
