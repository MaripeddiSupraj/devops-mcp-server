"""
tests/test_api.py
-----------------
Integration tests for the HTTP API layer.
No live AWS / GitHub / K8s / Terraform calls — errors at the integration
layer are expected and tested.
"""

from __future__ import annotations

import pytest


# ── Health probes ─────────────────────────────────────────────────────────────

class TestHealthProbes:
    def test_liveness_always_200(self, client):
        r = client.get("/health/live")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_readiness_returns_warnings_without_creds(self, client):
        r = client.get("/health/ready")
        assert r.status_code in (200, 503)
        body = r.json()
        assert "warnings" in body
        assert body["tools_registered"] > 100

    def test_legacy_health_alias(self, client):
        r = client.get("/health")
        assert r.status_code in (200, 503)


# ── Tools list ────────────────────────────────────────────────────────────────

class TestToolsEndpoints:
    def test_list_all_tools(self, client):
        r = client.get("/tools")
        assert r.status_code == 200
        body = r.json()
        assert body["count"] > 100
        assert len(body["tools"]) > 100

    def test_filter_by_tag_kubernetes(self, client):
        r = client.get("/tools?tag=kubernetes")
        assert r.status_code == 200
        body = r.json()
        assert body["count"] > 10
        for tool in body["tools"]:
            assert "kubernetes" in tool["tags"]

    def test_filter_by_tag_destructive(self, client):
        r = client.get("/tools?tag=destructive")
        assert r.status_code == 200
        assert r.json()["count"] >= 1
        names = [t["name"] for t in r.json()["tools"]]
        assert "terraform_destroy" in names

    def test_filter_unknown_tag_returns_empty(self, client):
        r = client.get("/tools?tag=nonexistent_tag")
        assert r.status_code == 200
        assert r.json()["count"] == 0

    def test_list_tags(self, client):
        r = client.get("/tools/tags")
        assert r.status_code == 200
        tags = r.json()
        assert "kubernetes" in tags
        assert "aws" in tags
        assert "terraform" in tags

    def test_describe_known_tool(self, client):
        r = client.get("/tools/k8s_get_pods")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "k8s_get_pods"
        assert "input_schema" in body
        assert "tags" in body

    def test_describe_unknown_tool_404(self, client):
        r = client.get("/tools/nonexistent")
        assert r.status_code == 404

    def test_tools_include_tags_field(self, client):
        r = client.get("/tools")
        for tool in r.json()["tools"]:
            assert "tags" in tool
            assert isinstance(tool["tags"], list)


# ── Execute ───────────────────────────────────────────────────────────────────

class TestExecuteEndpoint:
    def test_unknown_tool_returns_404(self, client):
        r = client.post("/tools/execute", json={"tool_name": "does_not_exist", "inputs": {}})
        assert r.status_code == 404

    def test_missing_required_input_returns_400(self, client):
        r = client.post("/tools/execute", json={"tool_name": "terraform_plan", "inputs": {}})
        assert r.status_code == 400
        assert "path" in r.json()["detail"]

    def test_extra_inputs_rejected(self, client):
        r = client.post("/tools/execute", json={
            "tool_name": "k8s_get_pods",
            "inputs": {"namespace": "default", "unknown_param": "bad"}
        })
        assert r.status_code == 400

    def test_response_has_request_id_header(self, client):
        r = client.post("/tools/execute", json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert "x-request-id" in r.headers

    def test_custom_request_id_echoed(self, client):
        r = client.post(
            "/tools/execute",
            json={"tool_name": "k8s_get_pods", "inputs": {}},
            headers={"X-Request-ID": "trace-abc-123"},
        )
        assert r.headers.get("x-request-id") == "trace-abc-123"

    def test_k8s_tool_fails_cleanly_without_cluster(self, client):
        r = client.post("/tools/execute", json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert r.status_code == 200
        assert r.json()["status"] == "error"
        assert r.json()["error"] is not None

    def test_aws_tool_fails_cleanly_without_creds(self, client):
        r = client.post("/tools/execute", json={"tool_name": "aws_list_ec2_instances", "inputs": {}})
        assert r.status_code == 200
        assert r.json()["status"] == "error"


# ── Batch execute ─────────────────────────────────────────────────────────────

class TestBatchExecute:
    def test_batch_runs_all_calls(self, client):
        r = client.post("/tools/execute/batch", json={"calls": [
            {"call_id": "a", "tool_name": "k8s_get_pods",  "inputs": {}},
            {"call_id": "b", "tool_name": "k8s_get_nodes", "inputs": {}},
        ]})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        assert body["succeeded"] + body["failed"] == 2

    def test_batch_failure_does_not_abort(self, client):
        r = client.post("/tools/execute/batch", json={"calls": [
            {"call_id": "ok",  "tool_name": "k8s_get_pods",  "inputs": {}},
            {"call_id": "bad", "tool_name": "nonexistent",   "inputs": {}},
            {"call_id": "ok2", "tool_name": "k8s_get_nodes", "inputs": {}},
        ]})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        ids = [res["call_id"] for res in body["results"]]
        assert ids == ["ok", "bad", "ok2"]

    def test_batch_oversize_rejected(self, client):
        calls = [{"tool_name": "k8s_get_pods", "inputs": {}} for _ in range(21)]
        r = client.post("/tools/execute/batch", json={"calls": calls})
        assert r.status_code == 422

    def test_batch_has_request_id(self, client):
        r = client.post("/tools/execute/batch", json={"calls": [
            {"tool_name": "k8s_get_pods", "inputs": {}}
        ]})
        assert "request_id" in r.json()


# ── Async jobs ────────────────────────────────────────────────────────────────

class TestAsyncJobs:
    def test_submit_async_returns_202(self, client):
        r = client.post("/tools/execute/async", json={
            "tool_name": "k8s_get_pods", "inputs": {}
        })
        assert r.status_code == 202
        body = r.json()
        assert "job_id" in body
        assert body["status"] == "pending"
        assert "/jobs/" in body["poll_url"]

    def test_poll_job_returns_status(self, client):
        submit = client.post("/tools/execute/async", json={
            "tool_name": "k8s_get_pods", "inputs": {}
        })
        job_id = submit.json()["job_id"]
        poll = client.get(f"/jobs/{job_id}")
        assert poll.status_code == 200
        assert poll.json()["job_id"] == job_id
        assert poll.json()["status"] in ("pending", "running", "success", "error")

    def test_poll_nonexistent_job_404(self, client):
        r = client.get("/jobs/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


# ── Security headers ──────────────────────────────────────────────────────────

class TestSecurityHeaders:
    def test_security_headers_present(self, client):
        r = client.get("/health/live")
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "DENY"
        assert "referrer-policy" in r.headers
