"""Tests for the claims read endpoints (service layer mocked)."""

from app.services import claims_service

_CLAIM_DETAIL = {
    "claim_id": "CL002",
    "cause": "Flood",
    "loss_date": "2023-01-20",
    "claim_date": None,
    "loss_amount": "50000.00",
    "payout_amount": "45000.00",
    "fraud_flag": False,
    "status": None,
    "policy": {
        "policy_id": "P1002",
        "policy_type": None,
        "coverage_limit": "150000.00",
        "premium_amount": None,
        "issue_date": "2021-07-15",
        "expiry_date": None,
        "status": None,
    },
    "customer": {
        "customer_id": "C002",
        "customer_name": "Alice Johnson",
        "city": "San Francisco",
        "state": "CA",
        "email": None,
    },
}


def test_get_claim_returns_detail(client, monkeypatch):
    monkeypatch.setattr(claims_service, "get_claim_detail", lambda db, cid: _CLAIM_DETAIL)
    response = client.get("/claims/CL002")
    assert response.status_code == 200
    body = response.json()
    assert body["claim_id"] == "CL002"
    assert body["customer"]["customer_name"] == "Alice Johnson"
    assert body["payout_amount"] == "45000.00"


def test_get_claim_not_found_returns_consistent_404(client, monkeypatch):
    monkeypatch.setattr(claims_service, "get_claim_detail", lambda db, cid: None)
    response = client.get("/claims/NOPE")
    assert response.status_code == 404
    body = response.json()
    # Consistent error envelope from the centralised handler.
    assert body["success"] is False
    assert body["error"] == "Not found"


def test_list_claims_returns_paginated_envelope(client, monkeypatch):
    canned = {
        "total_records": 1,
        "page": 1,
        "page_size": 20,
        "results": [
            {
                "claim_id": "CL013",
                "cause": "Flood",
                "loss_date": "2023-10-10",
                "claim_date": None,
                "loss_amount": "160000.00",
                "payout_amount": "144000.00",
                "fraud_flag": False,
                "policy_id": "P1002",
                "customer_id": "C002",
                "customer_name": "Alice Johnson",
                "city": "San Francisco",
                "state": "CA",
            }
        ],
    }
    monkeypatch.setattr(claims_service, "list_claims", lambda db, **kwargs: canned)
    response = client.get("/claims", params={"cause": "Flood"})
    assert response.status_code == 200
    body = response.json()
    assert body["total_records"] == 1
    assert body["results"][0]["claim_id"] == "CL013"


def test_list_claims_rejects_inverted_payout_range(client):
    # Validation happens before the service is called -> 400 with envelope.
    response = client.get("/claims", params={"min_payout": 100, "max_payout": 50})
    assert response.status_code == 400
    assert response.json()["success"] is False


def test_list_claims_rejects_bad_page(client):
    # page < 1 violates Query(ge=1) -> 422 from the validation handler.
    response = client.get("/claims", params={"page": 0})
    assert response.status_code == 422
    assert response.json()["error"] == "ValidationError"
