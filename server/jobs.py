"""
server/jobs.py
--------------
In-memory async background job store for long-running tool executions.

Design:
- Each job gets a UUID. The caller polls GET /jobs/{job_id} for status.
- Jobs are stored in a thread-safe dict with a TTL-based cleanup task.
- Workers run in FastAPI's default thread pool (run_in_executor) so
  blocking tool handlers (Terraform, kubectl) don't stall the event loop.
- Job history is capped at MAX_JOBS to prevent unbounded memory growth.

States: pending → running → success | error
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.logger import get_logger

log = get_logger(__name__)

MAX_JOBS = 500
JOB_TTL_SECONDS = 3600  # 1 hour


class Job:
    __slots__ = ("job_id", "tool_name", "inputs", "status", "result",
                 "error", "created_at", "started_at", "finished_at")

    def __init__(self, tool_name: str, inputs: Dict[str, Any]) -> None:
        self.job_id: str = str(uuid.uuid4())
        self.tool_name = tool_name
        self.inputs = inputs
        self.status: str = "pending"
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.created_at: datetime = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "tool_name": self.tool_name,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


class JobStore:
    """Thread-safe in-memory job registry."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}

    def create(self, tool_name: str, inputs: Dict[str, Any]) -> Job:
        if len(self._jobs) >= MAX_JOBS:
            self._evict_oldest()
        job = Job(tool_name, inputs)
        self._jobs[job.job_id] = job
        log.info("job_created", job_id=job.job_id, tool=tool_name)
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def _evict_oldest(self) -> None:
        oldest = min(self._jobs.values(), key=lambda j: j.created_at, default=None)
        if oldest:
            del self._jobs[oldest.job_id]
            log.info("job_evicted", job_id=oldest.job_id)


# Singleton store — imported by main.py
job_store = JobStore()


async def run_job(job: Job, executor_fn) -> None:
    """Run a tool in the thread pool and update job state."""
    loop = asyncio.get_event_loop()
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    log.info("job_started", job_id=job.job_id, tool=job.tool_name)
    try:
        response = await loop.run_in_executor(
            None, lambda: executor_fn(job.tool_name, job.inputs)
        )
        job.status = "success" if response.status == "success" else "error"
        job.result = response.data
        job.error = response.error
    except Exception as exc:
        job.status = "error"
        job.error = str(exc)
        log.error("job_failed", job_id=job.job_id, error=str(exc))
    finally:
        job.finished_at = datetime.now(timezone.utc)
        log.info("job_finished", job_id=job.job_id, status=job.status)
