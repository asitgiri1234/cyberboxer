"""Tests for optional rate limiting."""

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.rate_limit import rate_limit_exceeded_handler


def test_rate_limiting_disabled_by_default(client):
    # With rate limiting off (default), many rapid calls all succeed.
    codes = [client.get("/health").status_code for _ in range(30)]
    assert all(code == 200 for code in codes)


def test_rate_limiter_returns_429_when_limit_exceeded():
    # Self-contained app with a low limit, using the same limiter pattern and
    # 429 handler as the real app (avoids contaminating the global limiter).
    app = FastAPI()
    app.state.limiter = Limiter(
        key_func=get_remote_address, default_limits=["2/minute"], enabled=True
    )
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    @app.get("/ping")
    def ping(request: Request):  # `request` is required by slowapi
        return {"ok": True}

    test_client = TestClient(app, raise_server_exceptions=False)
    assert test_client.get("/ping").status_code == 200
    assert test_client.get("/ping").status_code == 200
    blocked = test_client.get("/ping")
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["success"] is False
    assert body["error"] == "RateLimitExceeded"
