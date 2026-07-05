"""
tests.test_integration
----------------------
End-to-end integration tests against a REAL PostgreSQL database.

Unlike the unit tests (which mock the session), these exercise the whole stack
— upload pipeline, ORM writes, joins, aggregates and the raw-SQL reports —
against live PostgreSQL. This is where the actual SQL is proven to run.

They are opt-in: set `TEST_DATABASE_URL` to a PostgreSQL URL (ideally a
dedicated throwaway database). If it is unset or unreachable, the whole module
is skipped, so a plain `pytest` run stays green without any database.

    # PowerShell
    $env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:pass@localhost:5432/insurance_claims_test"
    pytest tests/test_integration.py
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (register models on Base.metadata)
from app.database import Base, get_db
from app.main import app

pytestmark = pytest.mark.integration

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def _reachable(url: str) -> bool:
    """Return True if a database connection can be opened at `url`."""
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


# Skip the entire module unless a real, reachable test database is configured.
if not TEST_DATABASE_URL or not _reachable(TEST_DATABASE_URL):
    pytest.skip(
        "TEST_DATABASE_URL not set or database unreachable; skipping integration tests.",
        allow_module_level=True,
    )

_engine = create_engine(TEST_DATABASE_URL, future=True)
_TestSession = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)

DATA_DIR = "data"


def _sample_files() -> dict:
    """Read the three sample CSVs as multipart upload payloads."""
    return {
        name: (f"{name}.csv", open(f"{DATA_DIR}/{fname}", "rb").read(), "text/csv")
        for name, fname in (
            ("customer", "customer.csv"),
            ("policy", "policy.csv"),
            ("claims", "claims.csv"),
        )
    }


def _override_get_db():
    """Yield a session bound to the real test database."""
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    """Provide a TestClient wired to a fresh schema, seeded once with the CSVs.

    The schema is created from the ORM metadata, the sample data is uploaded
    once for the whole module, and everything is dropped on teardown.
    """
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    app.dependency_overrides[get_db] = _override_get_db

    test_client = TestClient(app, raise_server_exceptions=False)
    # Seed the database once; expose the upload response to the tests.
    response = test_client.post("/upload", files=_sample_files())
    test_client.upload_status = response.status_code
    test_client.upload_summary = response.json()

    yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=_engine)
    _engine.dispose()


def test_upload_persists_valid_rows_and_rejects_invalid(client):
    assert client.upload_status == 200
    summary = client.upload_summary
    assert summary["customers"]["inserted"] == 10
    assert summary["policies"]["inserted"] == 10   # 1 rejected: unknown customer
    assert summary["claims"]["inserted"] == 11     # 3 rejected: future/negative/bad-policy
    assert summary["total_records"] == 35
    reasons = {e["reason"] for e in summary["errors"]}
    assert "Customer not found" in reasons
    assert "Loss amount cannot be negative" in reasons
    assert "Loss date cannot be in the future" in reasons
    assert "Policy not found" in reasons


def test_claim_detail_joins_policy_and_customer(client):
    body = client.get("/claims/CL002").json()
    assert body["claim_id"] == "CL002"
    # CA + Flood => 10% deductible: 50000 -> 45000.
    assert body["payout_amount"] == "45000.00"
    assert body["policy"]["policy_id"] == "P1002"
    assert body["customer"]["customer_id"] == "C002"


def test_claim_detail_unknown_returns_404(client):
    resp = client.get("/claims/DOES_NOT_EXIST")
    assert resp.status_code == 404
    assert resp.json()["success"] is False


def test_search_filter_sort_paginate(client):
    body = client.get(
        "/claims",
        params={"cause": "Flood", "sort_by": "payout_amount", "order": "desc", "page_size": 2},
    ).json()
    assert body["total_records"] == 4
    assert body["page_size"] == 2
    assert body["results"][0]["claim_id"] == "CL013"        # highest flood payout
    assert body["results"][0]["payout_amount"] == "144000.00"


def test_top_customers_real_aggregate(client):
    data = client.get("/customers/top", params={"n": 3}).json()
    assert data[0]["customer_id"] == "C002"
    assert data[0]["total_claims"] == 4
    assert data[0]["total_payout"] == "246000.00"


def test_state_report_real_aggregate(client):
    report = client.get("/reports/state").json()
    california = next(row for row in report if row["state"] == "CA")
    assert california["total_claims"] == 5
    assert california["total_payout"] == "251000.00"
    assert california["maximum_payout"] == "144000.00"


def test_raw_sql_reports(client):
    top_cities = client.get("/reports/top-cities").json()
    assert top_cities[0]["city"] == "San Francisco"
    assert top_cities[0]["total_payout"] == "246000.00"

    by_cause = client.get("/reports/average-by-cause").json()
    assert any(r["cause"] == "Flood" and r["average_payout"] == "76500.00" for r in by_cause)


def test_health_against_real_db(client):
    body = client.get("/health").json()
    assert body["status"] == "healthy"
    assert body["database"] == "connected"
    assert "uptime" in body
