"""Tests for the optional in-process TTL cache."""

import time

from app.config import settings
from app.core import cache
from app.core.cache import cached


def _make_counter_fn():
    """Return a decorated function that counts real (non-cached) executions."""
    calls = {"count": 0}

    @cached("test_prefix")
    def compute(db, limit=10):
        calls["count"] += 1
        return {"limit": limit, "call": calls["count"]}

    return compute, calls


def test_cache_disabled_by_default_calls_through(monkeypatch):
    monkeypatch.setattr(settings, "CACHE_ENABLED", False)
    cache.invalidate()
    compute, calls = _make_counter_fn()
    compute(None)
    compute(None)
    assert calls["count"] == 2  # no caching: every call executes


def test_cache_enabled_serves_second_call_from_cache(monkeypatch):
    monkeypatch.setattr(settings, "CACHE_ENABLED", True)
    cache.invalidate()
    compute, calls = _make_counter_fn()
    first = compute(None)
    second = compute(None)
    assert calls["count"] == 1          # second call was a cache hit
    assert first == second


def test_cache_key_includes_arguments(monkeypatch):
    monkeypatch.setattr(settings, "CACHE_ENABLED", True)
    cache.invalidate()
    compute, calls = _make_counter_fn()
    compute(None, limit=5)
    compute(None, limit=7)              # different args -> different key
    assert calls["count"] == 2


def test_invalidate_clears_cached_entries(monkeypatch):
    monkeypatch.setattr(settings, "CACHE_ENABLED", True)
    cache.invalidate()
    compute, calls = _make_counter_fn()
    compute(None)
    cache.invalidate()                  # what the upload pipeline triggers
    compute(None)
    assert calls["count"] == 2


def test_entries_expire_after_ttl(monkeypatch):
    monkeypatch.setattr(settings, "CACHE_ENABLED", True)
    monkeypatch.setattr(settings, "CACHE_TTL_SECONDS", 0)  # expire immediately
    cache.invalidate()
    compute, calls = _make_counter_fn()
    compute(None)
    time.sleep(0.01)
    compute(None)
    assert calls["count"] == 2          # TTL elapsed -> recomputed
