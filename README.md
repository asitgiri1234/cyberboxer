# Insurance Claims REST API

A production-quality REST API for ingesting and analysing insurance claims,
built with **FastAPI**, **SQLAlchemy 2.x** and **PostgreSQL**, following a clean,
layered architecture.

The service ingests three CSV datasets (customers, policies, claims), cleans and
validates them, applies business rules (payout calculation + fraud detection),
persists the results, and exposes read APIs and reports.

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
- [API endpoints](#api-endpoints)
- [Business rules](#business-rules-implemented)
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

Tables are created automatically on startup via `create_tables()` (SQLAlchemy
`create_all`, idempotent) when `AUTO_CREATE_TABLES=true`. For production schema
evolution, introduce **Alembic** migrations and set `AUTO_CREATE_TABLES=false`.

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

## Testing

```bash
pytest
```

Tests run **without a database**: pure logic (business rules, CSV cleaning) is
tested directly, and endpoints are tested with a mocked session and monkeypatched
services, so the suite is fast and hermetic.

## Docker

```bash
docker compose up --build      # starts PostgreSQL + the API
```

The API will be available at <http://localhost:8000>.

## Assumptions

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

- Alembic migrations (replace `create_all`).
- Authentication (JWT / API key) and per-client rate limiting.
- Async database access (`asyncpg` + async SQLAlchemy) for higher concurrency.
- Idempotent/upsert uploads and background processing for very large files.
- Caching for expensive reports; pagination cursors for large result sets.
