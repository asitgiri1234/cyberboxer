"""
app.core.jobs
------------
Minimal in-memory, thread-safe job registry for background tasks.

Each job is a dict with a stable shape:

    {"job_id", "status", "submitted_at", "finished_at", "summary", "error"}

`status` is one of "pending" | "completed" | "failed". The store is in-process
(a lock-guarded dict), which fits the single-process deployment; for multiple
workers it would be swapped for Redis or a database table without changing the
API surface.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def create() -> str:
    """Register a new pending job and return its id."""
    job_id = uuid.uuid4().hex
    with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "summary": None,
            "error": None,
        }
    return job_id


def complete(job_id: str, summary: dict[str, Any]) -> None:
    """Mark a job as completed with its result summary."""
    _finish(job_id, status="completed", summary=summary)


def fail(job_id: str, error: str) -> None:
    """Mark a job as failed with a short error message."""
    _finish(job_id, status="failed", error=error)


def get(job_id: str) -> dict[str, Any] | None:
    """Return a copy of the job record, or None if unknown."""
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def _finish(job_id: str, *, status: str, summary: dict[str, Any] | None = None,
            error: str | None = None) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:  # job evicted/unknown; nothing to record
            return
        job["status"] = status
        job["finished_at"] = datetime.now(timezone.utc).isoformat()
        job["summary"] = summary
        job["error"] = error
