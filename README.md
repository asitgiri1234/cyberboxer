# Insurance Claims REST API

A production-quality REST API for ingesting and analysing insurance claims,
built with **FastAPI**, **SQLAlchemy 2.x** and **PostgreSQL**, following a clean,
layered architecture.

The service ingests three CSV datasets (customers, policies, claims), cleans and
validates them, applies business rules (payout calculation + fraud detection),
persists the results, and exposes read APIs and reports.

---

## Quick start (Docker)

The fastest way to run the whole stack (PostgreSQL + API + migrations) with no
local database setup:

```bash
docker compose up --build
```

This starts PostgreSQL, applies the Alembic migrations, and launches the API.
Then open the interactive docs and load the sample data:

- Swagger UI: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

```bash
# load the provided sample datasets
curl -X POST http://localhost:8000/upload \
  -F "customer=@data/customer.csv;type=text/csv" \
  -F "policy=@data/policy.csv;type=text/csv" \
  -F "claims=@data/claims.csv;type=text/csv"
```

Prefer to run it without Docker? See [Setup](#setup) below.

---

## Table of contents

- [Features](#features)
- [Technology stack](#technology-stack)
- [Architecture](#project-architecture)
- [Folder structure](#folder-structure)
- [Setup](#setup)
- [Environment variables](#environment-variables)
- [Running PostgreSQL](#running-postgresql)
- [Running the application](#running-the-application)
- [Database Migrations](#database-migrations)
- [API endpoints](#api-endpoints)
- [Business rules](#business-rules-implemented)
- [Authentication](#authentication)
- [Testing](#testing)
- [Docker](#docker)
- [Assumptions](#assumptions)
- [Future improvements](#future-improvements)

---

## Features

- **CSV upload pipeline** — `POST /upload` ingests `customer.csv`, `policy.csv`,
  `claims.csv` as multipart form data.
- **Pandas preprocessing** — column standardisation (snake_case), whitespace
  trimming, missing-value normalisation, de-duplication, numeric/date coercion.
- **Validation** — structural (required columns, headers) and relational
  (foreign-key integrity) validation; bad rows are rejected individually.
- **Business rules** — payout calculation (minor rule, CA-flood deductible,
  coverage cap, non-negative floor) and fraud detection.
- **Read APIs** — single claim detail, filtered/sorted/paginated claim search.
- **Reports** — per-state aggregates plus two raw-SQL reports.
- **Production concerns** — centralised exception handling, request-logging
  middleware, gzip compression, structured logging, Swagger docs, tests.

## Technology stack

| Concern            | Choice                              |
|--------------------|-------------------------------------|
| Web framework      | FastAPI                             |
| ORM                | SQLAlchemy 2.x (typed, `Mapped`)    |
| Database           | PostgreSQL                          |
| Driver             | psycopg 3                           |
| Data preprocessing | pandas                              |
| Config             | pydantic-settings + python-dotenv   |
| Validation/schemas | Pydantic v2                         |
| Server             | Uvicorn (ASGI)                      |
| Tests              | pytest + Starlette TestClient       |

## Project architecture

The project is organised into clear layers, each with a single responsibility:

```
Routes (HTTP)  ->  Services (business/query logic)  ->  Models (ORM)  ->  PostgreSQL
     |                     |
   Schemas            Core (exception handlers, middleware)
 (Pydantic I/O)
```

- **Routes** are thin: they parse/validate inputs, call a service, and shape the
  HTTP response. They contain no business logic or SQL.
- **Services** hold all logic: the upload pipeline, pure business rules, and
  read/report queries. Pure logic (`business_rules.py`) has no I/O, so it is
  trivially unit-testable.
- **Models** are SQLAlchemy declarative classes with typed columns and
  bidirectional relationships.
- **Schemas** (Pydantic) define response shapes, documenting Swagger and
  guaranteeing only required fields are returned.
- **Core** provides cross-cutting infrastructure (consistent error handling,
  request logging).

This separation makes the code easy to test, reason about, and extend.

## Folder structure

```
cyberboxer/
├── app/
│   ├── main.py                 # App factory: metadata, middleware, handlers, routers
│   ├── config.py               # Typed settings from env / .env
│   ├── database.py             # Engine, SessionLocal, Base, get_db, create_tables
│   ├── core/
│   │   ├── exception_handlers.py   # Centralised, consistent error responses
│   │   └── middleware.py           # Request logging middleware
│   ├── models/                 # SQLAlchemy models
│   │   ├── customer.py  policy.py  claim.py  mixins.py
│   ├── schemas/                # Pydantic response models
│   │   ├── claim.py  customer.py  report.py  common.py
│   ├── routes/                 # Thin HTTP handlers
│   │   ├── health.py  upload.py  claims.py  customers.py  reports.py
│   ├── services/               # Business & query logic
│   │   ├── csv_cleaner.py  data_validator.py  upload_service.py
│   │   ├── business_rules.py  claims_service.py
│   │   ├── customers_service.py  reports_service.py
│   └── utils/logger.py         # Console + rotating-file logging
├── alembic/                    # Database migrations
│   ├── env.py                  # Reuses app config + Base.metadata
│   ├── script.py.mako
│   └── versions/               # Migration scripts
├── alembic.ini                 # Alembic config (URL injected from settings)
├── tests/                      # pytest suite
├── data/                       # Sample CSV datasets
├── Dockerfile  docker-compose.yml  Makefile
├── requirements.txt  .env.example  pytest.ini
└── README.md
```

## Setup

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env      # then edit DATABASE_URL
```

## Environment variables

| Variable             | Default                | Description                                   |
|----------------------|------------------------|-----------------------------------------------|
| `DATABASE_URL`       | *(required)*           | SQLAlchemy URL, e.g. `postgresql+psycopg://user:pass@localhost:5432/insurance_claims` |
| `LOG_LEVEL`          | `INFO`                 | Logging level                                 |
| `LOG_FILE`           | `logs/app.log`         | Log file path                                 |
| `AUTO_CREATE_TABLES` | `true`                 | Auto-create tables on startup (dev only)      |

## Running PostgreSQL

Use an existing PostgreSQL instance, or start one with Docker:

```bash
docker run --name claims-db -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=insurance_claims -p 5432:5432 -d postgres:18-alpine
```

Then set `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/insurance_claims`.

### Migrations

The schema is managed with **Alembic** migrations. The application never creates
tables on startup. Before first run (and after pulling schema changes), apply
the migrations:

```bash
alembic upgrade head
```

See [Database Migrations](#database-migrations) for the full command reference.

## Running the application

```bash
uvicorn app.main:app --reload
```

- API: <http://localhost:8000>
- **Swagger UI**: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

Then load the sample data:

```bash
curl -X POST http://localhost:8000/upload \
  -F "customer=@data/customer.csv;type=text/csv" \
  -F "policy=@data/policy.csv;type=text/csv" \
  -F "claims=@data/claims.csv;type=text/csv"
```

## Database Migrations

**Why Alembic?** The schema is version-controlled and evolves through reviewable
migration scripts instead of `create_all()`. This makes changes reproducible,
reversible, and identical across development, CI and production — the safe,
industry-standard approach. The application no longer creates tables on startup.

Alembic reuses the app's configuration: the database URL comes from
`app.config.settings` (i.e. your `.env`) via `alembic/env.py`, and migrations are
autogenerated against `Base.metadata`, so there is no duplicated configuration.

**Initialize / apply the schema** (first run and after pulling changes):

```bash
alembic upgrade head          # create/upgrade the schema to the latest revision
```

**Common commands:**

```bash
# Autogenerate a migration after changing the SQLAlchemy models
alembic revision --autogenerate -m "add claim_status column"

# Create an empty migration to edit by hand
alembic revision -m "custom data backfill"

# Apply migrations
alembic upgrade head          # to the latest
alembic upgrade +1            # one step forward

# Roll back
alembic downgrade -1          # one step back
alembic downgrade base        # remove everything

# Inspect
alembic current               # current revision of the database
alembic history --verbose     # full migration history
```

> After autogenerating, always **review** the migration in `alembic/versions/`
> before committing — autogenerate is a strong draft, not a guarantee.

## API endpoints

| Method | Path                        | Description                                        |
|--------|-----------------------------|----------------------------------------------------|
| GET    | `/health`                   | Service + database health check                    |
| POST   | `/upload`                   | Upload the three CSV files                          |
| GET    | `/claims/{claim_id}`        | Single claim with policy, customer, payout, fraud  |
| GET    | `/claims`                   | Filter / sort / paginate claims                    |
| GET    | `/customers/top?n=10`       | Customers ranked by total payout                   |
| GET    | `/reports/state`            | Aggregates grouped by state                        |
| GET    | `/reports/top-cities`       | Raw-SQL: top cities by payout                      |
| GET    | `/reports/average-by-cause` | Raw-SQL: average payout by cause                   |

`GET /claims` filters: `city`, `state`, `cause`, `start_date`, `end_date`,
`min_payout`, `max_payout`; sorting: `sort_by` (`claim_date`, `loss_date`,
`payout_amount`, `loss_amount`, `city`, `state`) and `order` (`asc`/`desc`);
pagination: `page`, `page_size`.

All errors share one envelope:

```json
{ "success": false, "error": "Not found", "message": "Claim 'CL999' does not exist" }
```

## Business rules implemented

1. Loss amount cannot be negative.
2. Loss date cannot be in the future.
3. Claim date cannot be earlier than the policy issue date.
4. Final payout cannot exceed the policy coverage limit.
5. Final payout cannot be negative.
6. Customers younger than 18 receive only 50% payout.
7. Flood claims in California incur an additional 10% deductible.
8. Customers with more than 5 claims are flagged (`fraud_flag = True`).
9. Duplicate claims are never inserted.
10. Policies referencing non-existent customers are rejected.

Payout order: `loss → minor rule → CA-flood deductible → coverage cap →
non-negative floor → round to cents`.

## Authentication

Optional API-key authentication, **disabled by default** (so the API is easy to
evaluate). Enable it by setting two environment variables:

```bash
AUTH_ENABLED=true
API_KEY=your-secret-key
```

When enabled, the data endpoints (`/upload`, `/claims`, `/customers`,
`/reports`) require the header `X-API-Key: your-secret-key`. `/health` and the
docs stay public. Responses:

- missing header → `401 Unauthorized`
- wrong key → `403 Forbidden`
- correct key → normal response

```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/reports/state
```

The scheme is registered in OpenAPI, so Swagger shows an **Authorize** button.

## Testing

```bash
pytest                     # unit tests (fast, no database)
```

**Unit tests** run **without a database**: pure logic (business rules, CSV
cleaning) is tested directly, and endpoints are tested with a mocked session and
monkeypatched services, so the suite is fast and hermetic.

**Integration tests** (`tests/test_integration.py`) exercise the whole stack —
upload, ORM writes, joins, aggregates and the raw-SQL reports — against a real
PostgreSQL database. They are opt-in: point `TEST_DATABASE_URL` at a throwaway
database and they run; otherwise they are skipped (so a plain `pytest` stays
green anywhere).

```bash
# create a throwaway DB first, e.g. insurance_claims_test, then:
# PowerShell
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:pass@localhost:5432/insurance_claims_test"
pytest tests/test_integration.py
```

## Docker

```bash
docker compose up --build      # starts PostgreSQL + the API
```

The API will be available at <http://localhost:8000>.

## Assumptions & design decisions

- **Database:** PostgreSQL is used (the brief allows PostgreSQL or SQLite). To
  keep it zero-setup for a reviewer, `docker compose up --build` starts Postgres,
  runs the Alembic migrations, and launches the API together — no manual DB
  install needed.
- **Upload response** is a superset of the brief's example: it includes the
  top-level `total_records` / `inserted` / `rejected`, plus a per-file breakdown
  and structured `errors` (`{file, row, reason}`) for precise debugging.
- The sample datasets use a single `name` column and an `age` column; `name` is
  split into `first_name`/`last_name`, and `age` drives the minor rule (it is not
  persisted, as the schema stores `date_of_birth`).
- The `state` used by the CA-flood rule and reports is the **customer's** state.
- `GET /claims` date-range filters apply to `loss_date` (the populated date in the
  datasets); `claim_date` is nullable.
- Monetary values are serialised as JSON strings (`Decimal`) to preserve precision.
- Exact-duplicate CSV rows are silently de-duplicated and excluded from totals.
- Dates are parsed by pandas, whose nanosecond `Timestamp` supports roughly
  `1677`–`2262`; dates outside that range are coerced to null. Realistic
  future dates are still rejected by the business rule (verified with `2027`/`2030`).

## Future improvements

- Per-client rate limiting; JWT/OAuth2 (an optional API-key scheme is included).
- Async database access (`asyncpg` + async SQLAlchemy) for higher concurrency.
- Idempotent/upsert uploads and background processing for very large files.
- Caching for expensive reports; pagination cursors for large result sets.
