"""Tests for the background (async) upload job flow.

With TestClient, FastAPI background tasks run synchronously right after the
response is produced, so the job outcome can be asserted immediately. The
pipeline itself (`upload_service.process_upload`) is monkeypatched so no real
database is needed.
"""

from app.services import upload_jobs

_CANNED_SUMMARY = {
    "total_records": 3,
    "inserted": 3,
    "rejected": 0,
    "customers": {"total": 1, "inserted": 1, "rejected": 0},
    "policies": {"total": 1, "inserted": 1, "rejected": 0},
    "claims": {"total": 1, "inserted": 1, "rejected": 0},
    "errors": [],
}

_FILES = {
    "customer": ("customer.csv", b"customer_id,name\nC1,A", "text/csv"),
    "policy": ("policy.csv", b"policy_id,customer_id\nP1,C1", "text/csv"),
    "claims": ("claims.csv", b"claim_id,policy_id\nCL1,P1", "text/csv"),
}


def test_async_upload_returns_202_and_completes(client, monkeypatch):
    monkeypatch.setattr(
        upload_jobs.upload_service, "process_upload", lambda c, p, cl, db: _CANNED_SUMMARY
    )
    response = client.post("/upload/async", files=_FILES)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["status_url"].endswith(body["job_id"])

    # Background task has already run (TestClient executes it post-response).
    job = client.get(f"/upload/jobs/{body['job_id']}").json()
    assert job["status"] == "completed"
    assert job["summary"] == _CANNED_SUMMARY
    assert job["finished_at"] is not None
    assert job["error"] is None


def test_async_upload_failure_is_recorded_on_job(client, monkeypatch):
    def boom(c, p, cl, db):
        raise RuntimeError("simulated pipeline crash")

    monkeypatch.setattr(upload_jobs.upload_service, "process_upload", boom)
    response = client.post("/upload/async", files=_FILES)
    assert response.status_code == 202

    job = client.get(f"/upload/jobs/{response.json()['job_id']}").json()
    assert job["status"] == "failed"
    assert "simulated pipeline crash" in job["error"]
    assert job["summary"] is None


def test_unknown_job_returns_404(client):
    response = client.get("/upload/jobs/does-not-exist")
    assert response.status_code == 404
    assert response.json()["success"] is False


def test_async_upload_missing_files_returns_422(client):
    response = client.post(
        "/upload/async", files={"customer": ("c.csv", b"customer_id\nC1", "text/csv")}
    )
    assert response.status_code == 422
