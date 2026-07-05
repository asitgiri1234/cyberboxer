"""Tests for the health endpoint (DB session mocked)."""


def test_health_reports_healthy_when_db_reachable(client, db):
    # db.execute returns a MagicMock (no exception) -> healthy.
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["database"] == "connected"
    assert "uptime" in body  # process uptime is reported


def test_health_reports_unhealthy_when_db_unreachable(client, db):
    db.execute.side_effect = Exception("connection refused")
    response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unhealthy"
    assert body["database"] == "disconnected"
