"""
app.core.cache
-------------
Optional in-process TTL cache for expensive read queries (the report
aggregates). Deliberately dependency-free — a dict of `key -> (expires, value)`
guarded by a lock — which is plenty for a single-process API and easy to swap
for Redis later.

* Enabled only when `settings.CACHE_ENABLED` is True (default False), so
  evaluators always see live data unless they opt in.
* Entries expire after `settings.CACHE_TTL_SECONDS`.
* `invalidate()` clears everything; the upload pipeline calls it after a
  successful import so reports never serve stale aggregates.

Usage — decorate a service function whose FIRST argument is the DB session
(the session is excluded from the cache key):

    @cached("state_report")
    def get_state_report(db): ...
"""

from __future__ import annotations

import logging
import threading
import time
from functools import wraps
from typing import Any, Callable, TypeVar

from app.config import settings

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_lock = threading.Lock()
_store: dict[str, tuple[float, Any]] = {}


def _make_key(prefix: str, args: tuple, kwargs: dict) -> str:
    """Build a cache key from the call arguments (DB session excluded)."""
    return f"{prefix}:{args!r}:{sorted(kwargs.items())!r}"


def get(key: str) -> tuple[bool, Any]:
    """Return `(hit, value)`; expired entries count as misses and are removed."""
    with _lock:
        entry = _store.get(key)
        if entry is None:
            return False, None
        expires, value = entry
        if time.time() >= expires:
            del _store[key]
            return False, None
        return True, value


def set(key: str, value: Any) -> None:
    """Store `value` under `key` with the configured TTL."""
    with _lock:
        _store[key] = (time.time() + settings.CACHE_TTL_SECONDS, value)


def invalidate() -> None:
    """Drop every cached entry (called after each successful upload)."""
    with _lock:
        if _store:
            logger.info("Cache invalidated (%d entries dropped)", len(_store))
        _store.clear()


def cached(prefix: str) -> Callable[[F], F]:
    """Cache a service function's result for the configured TTL.

    The wrapped function's first positional argument (the DB session) is
    excluded from the key. A no-op when CACHE_ENABLED is False.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(db, *args: Any, **kwargs: Any) -> Any:
            if not settings.CACHE_ENABLED:
                return func(db, *args, **kwargs)

            key = _make_key(prefix, args, kwargs)
            hit, value = get(key)
            if hit:
                return value

            value = func(db, *args, **kwargs)
            set(key, value)
            return value

        return wrapper  # type: ignore[return-value]

    return decorator
