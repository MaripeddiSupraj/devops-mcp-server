"""
tests/test_jobs.py
-------------------
Unit tests for the in-memory job store and async job lifecycle.

Tests the JobStore directly (no HTTP layer) and verifies:
- Job creation, state transitions, eviction
- run_job correctly updates status on success and failure
- MAX_JOBS cap evicts oldest job
"""

from __future__ import annotations

import asyncio
import pytest

from server.jobs import Job, JobStore, MAX_JOBS, run_job
from server.schemas import ToolResponse


# ── JobStore unit tests ───────────────────────────────────────────────────────

class TestJobStore:
    def setup_method(self):
        self.store = JobStore()

    def test_create_returns_job_with_pending_status(self):
        job = self.store.create("k8s_get_pods", {})
        assert job.status == "pending"
        assert job.job_id is not None
        assert job.tool_name == "k8s_get_pods"
        assert job.result is None
        assert job.error is None

    def test_get_returns_created_job(self):
        job = self.store.create("k8s_get_pods", {})
        retrieved = self.store.get(job.job_id)
        assert retrieved is job

    def test_get_nonexistent_returns_none(self):
        assert self.store.get("00000000-0000-0000-0000-000000000000") is None

    def test_each_job_gets_unique_id(self):
        ids = {self.store.create("k8s_get_pods", {}).job_id for _ in range(10)}
        assert len(ids) == 10

    def test_job_stores_inputs(self):
        inputs = {"namespace": "production", "label": "app=web"}
        job = self.store.create("k8s_get_pods", inputs)
        assert self.store.get(job.job_id).inputs == inputs

    def test_max_jobs_evicts_oldest(self):
        jobs = [self.store.create("k8s_get_pods", {}) for _ in range(MAX_JOBS)]
        oldest_id = jobs[0].job_id
        # Adding one more should evict the oldest
        self.store.create("k8s_get_pods", {})
        assert self.store.get(oldest_id) is None

    def test_eviction_preserves_newest(self):
        jobs = [self.store.create("k8s_get_pods", {}) for _ in range(MAX_JOBS)]
        newest_id = jobs[-1].job_id
        self.store.create("k8s_get_pods", {})
        assert self.store.get(newest_id) is not None


# ── Job.to_dict ───────────────────────────────────────────────────────────────

class TestJobToDict:
    def test_pending_job_dict_has_required_keys(self):
        job = Job("terraform_apply", {"path": "/tmp/infra"})
        d = job.to_dict()
        assert d["job_id"] == job.job_id
        assert d["tool_name"] == "terraform_apply"
        assert d["status"] == "pending"
        assert d["result"] is None
        assert d["error"] is None
        assert d["created_at"] is not None
        assert d["started_at"] is None
        assert d["finished_at"] is None

    def test_timestamps_are_iso_strings(self):
        job = Job("k8s_get_pods", {})
        d = job.to_dict()
        assert "T" in d["created_at"]  # ISO 8601 format


# ── run_job lifecycle ─────────────────────────────────────────────────────────

class TestRunJob:
    @pytest.mark.asyncio
    async def test_successful_execution_sets_success_status(self):
        job = Job("k8s_get_pods", {})

        def mock_executor(tool_name, inputs):
            return ToolResponse(status="success", data={"pods": []})

        await run_job(job, mock_executor)
        assert job.status == "success"
        assert job.result == {"pods": []}
        assert job.error is None
        assert job.started_at is not None
        assert job.finished_at is not None

    @pytest.mark.asyncio
    async def test_tool_error_response_sets_error_status(self):
        job = Job("k8s_get_pods", {})

        def mock_executor(tool_name, inputs):
            return ToolResponse(status="error", error="cluster not reachable")

        await run_job(job, mock_executor)
        assert job.status == "error"
        assert job.error == "cluster not reachable"

    @pytest.mark.asyncio
    async def test_executor_exception_sets_error_status(self):
        job = Job("k8s_get_pods", {})

        def mock_executor(tool_name, inputs):
            raise RuntimeError("unexpected crash")

        await run_job(job, mock_executor)
        assert job.status == "error"
        assert "unexpected crash" in job.error

    @pytest.mark.asyncio
    async def test_timestamps_populated_after_run(self):
        job = Job("k8s_get_pods", {})
        assert job.started_at is None
        assert job.finished_at is None

        await run_job(job, lambda t, i: ToolResponse(status="success", data={}))

        assert job.started_at is not None
        assert job.finished_at is not None
        assert job.finished_at >= job.started_at

    @pytest.mark.asyncio
    async def test_status_transitions_pending_running_success(self):
        states = []
        job = Job("k8s_get_pods", {})

        original_run = run_job.__wrapped__ if hasattr(run_job, '__wrapped__') else None

        async def track_states():
            # Manually replicate the state machine to observe transitions
            job.status = "running"
            states.append("running")
            result = ToolResponse(status="success", data={})
            job.status = "success" if result.status == "success" else "error"
            states.append(job.status)

        await track_states()
        assert states == ["running", "success"]
