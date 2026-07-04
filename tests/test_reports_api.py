"""Tests for the customers and reports read endpoints (service layer mocked)."""

from app.services import customers_service, reports_service


def test_top_customers_returns_ranked_list(client, monkeypatch):
    canned = [
        {
            "customer_id": "C002",
            "customer_name": "Alice Johnson",
            "total_claims": 4,
            "total_payout": "246000.00",
            "fraud_flag": False,
        }
    ]
    monkeypatch.setattr(customers_service, "get_top_customers", lambda db, limit: canned)
    response = client.get("/customers/top", params={"n": 5})
    assert response.status_code == 200
    body = response.json()
    assert body[0]["customer_id"] == "C002"
    assert body[0]["total_claims"] == 4


def test_top_customers_rejects_invalid_n(client):
    response = client.get("/customers/top", params={"n": 0})
    assert response.status_code == 422


def test_state_report_returns_aggregates(client, monkeypatch):
    canned = [
        {
            "state": "CA",
            "total_claims": 5,
            "average_payout": "50200.00",
            "maximum_payout": "144000.00",
            "total_payout": "251000.00",
        }
    ]
    monkeypatch.setattr(reports_service, "get_state_report", lambda db: canned)
    response = client.get("/reports/state")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["state"] == "CA"
    assert body[0]["total_payout"] == "251000.00"


def test_top_cities_raw_sql_report(client, monkeypatch):
    canned = [{"city": "San Francisco", "total_claims": 4, "total_payout": "246000.00"}]
    monkeypatch.setattr(reports_service, "get_top_cities_by_payout", lambda db, limit: canned)
    response = client.get("/reports/top-cities", params={"limit": 5})
    assert response.status_code == 200
    assert response.json()[0]["city"] == "San Francisco"


def test_average_by_cause_raw_sql_report(client, monkeypatch):
    canned = [{"cause": "Flood", "total_claims": 4, "average_payout": "76500.00"}]
    monkeypatch.setattr(reports_service, "get_average_payout_by_cause", lambda db: canned)
    response = client.get("/reports/average-by-cause")
    assert response.status_code == 200
    assert response.json()[0]["cause"] == "Flood"
