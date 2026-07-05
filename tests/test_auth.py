"""Tests for the optional API-key authentication (DB session mocked)."""

from app.config import settings
from app.services import reports_service


def test_data_endpoint_open_when_auth_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", False)
    monkeypatch.setattr(reports_service, "get_state_report", lambda db: [])
    response = client.get("/reports/state")
    assert response.status_code == 200


def test_missing_key_returns_401_when_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "API_KEY", "secret")
    response = client.get("/reports/state")
    assert response.status_code == 401
    assert response.json()["error"] == "Unauthorized"


def test_wrong_key_returns_403_when_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "API_KEY", "secret")
    response = client.get("/reports/state", headers={"X-API-Key": "wrong"})
    assert response.status_code == 403
    assert response.json()["error"] == "Forbidden"


def test_correct_key_allows_access(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "API_KEY", "secret")
    monkeypatch.setattr(reports_service, "get_state_report", lambda db: [])
    response = client.get("/reports/state", headers={"X-API-Key": "secret"})
    assert response.status_code == 200


def test_health_stays_public_when_auth_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "API_KEY", "secret")
    # No API key supplied, but /health is intentionally unprotected.
    response = client.get("/health")
    assert response.status_code == 200
