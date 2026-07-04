"""
tests.conftest
-------------
Shared pytest fixtures.

Tests run WITHOUT a real database: the settings point at an unused in-memory
SQLite URL (the engine is created lazily and never connected), auto table
creation is disabled, and the `get_db` dependency is overridden with a
`MagicMock` session. Service functions are monkeypatched per test where a
query result is needed. This keeps the suite fast, hermetic and CI-friendly.
"""

from __future__ import annotations

import os

# These MUST be set before `app` (and therefore `app.config`) is imported.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["AUTO_CREATE_TABLES"] = "false"

from unittest.mock import MagicMock  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def db() -> MagicMock:
    """A mock database session injected into request handlers."""
    return MagicMock()


@pytest.fixture
def client(db: MagicMock):
    """A TestClient with `get_db` overridden to yield the mock session.

    The app is NOT used as a context manager, so the lifespan (which would try
    to create tables) does not run.
    """

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    test_client = TestClient(app, raise_server_exceptions=False)
    yield test_client
    app.dependency_overrides.clear()
