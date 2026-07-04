# Insurance Claims REST API

A production-quality REST API for managing insurance claims, built with
**FastAPI**, **SQLAlchemy 2.x** and **PostgreSQL**, following clean
architecture principles.

> **Phase 1 (this repo):** project foundation only — configuration, database
> wiring, logging and a health-check endpoint. No business logic, models or
> claim endpoints yet.

## Project structure

```
cyberboxer/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app entry point (metadata, routers, lifespan)
│   ├── config.py          # Typed settings loaded from environment / .env
│   ├── database.py        # SQLAlchemy engine, SessionLocal, declarative Base
│   ├── routes/
│   │   ├── __init__.py
│   │   └── health.py      # GET /health endpoint (verifies DB connectivity)
│   └── utils/
│       ├── __init__.py
│       └── logger.py      # Console + rotating-file logging setup
├── logs/
│   └── .gitkeep           # Keeps the logs directory in git (logs are ignored)
├── .env.example           # Sample environment configuration
├── .gitignore
├── requirements.txt
└── README.md
```

## Getting started

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
cp .env.example .env        # then edit DATABASE_URL for your PostgreSQL instance
```

### 4. Run the application

```bash
uvicorn app.main:app --reload
```

- API root: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

## Health check

```
GET /health
```

Response when the database is reachable:

```json
{
    "status": "healthy",
    "database": "connected"
}
```

If PostgreSQL is unreachable the endpoint returns HTTP `503` with
`{"status": "unhealthy", "database": "disconnected"}`.
