"""
tests/test_api.py
-----------------
Integration tests for the FastAPI HTTP layer.
No live AWS / GitHub / Kubernetes / Terraform calls are made —
tool handlers are mocked at the registry level.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.main import app, registry
from server.registry import ToolEntry


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ── /health ───────────────────────────────────────────────────────────────────

class TestHealth:
    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_response_body(self, client):
        body = client.get("/health").json()
        assert body["status"] == "ok"
        assert isinstance(body["tools_registered"], int)


# ── /tools ────────────────────────────────────────────────────────────────────

class TestListTools:
    def test_returns_200(self, client):
        assert client.get("/tools").status_code == 200

    def test_response_has_tools_list(self, client):
        body = client.get("/tools").json()
        assert "tools" in body
        assert isinstance(body["tools"], list)
        assert body["count"] == len(body["tools"])

    def test_each_tool_has_required_fields(self, client):
        tools = client.get("/tools").json()["tools"]
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool


# ── /tools/{tool_name} ───────────────────────────────────────────────────────

class TestDescribeTool:
    def test_known_tool(self, client):
        resp = client.get("/tools/terraform_plan")
        assert resp.status_code == 200
        assert resp.json()["name"] == "terraform_plan"

    def test_unknown_tool_404(self, client):
        resp = client.get("/tools/does_not_exist")
        assert resp.status_code == 404


# ── /tools/execute ────────────────────────────────────────────────────────────

class TestExecuteTool:
    def test_unknown_tool_returns_error(self, client):
        resp = client.post(
            "/tools/execute",
            json={"tool_name": "ghost_tool", "inputs": {}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "error"
        assert "not registered" in body["error"]

    def test_validation_failure_returns_error(self, client):
        # terraform_plan requires "path" — omit it deliberately
        resp = client.post(
            "/tools/execute",
            json={"tool_name": "terraform_plan", "inputs": {}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "error"

    def test_mocked_tool_success(self, client, monkeypatch):
        """Register a lightweight mock tool and verify the execute endpoint."""

        def _mock_handler(msg: str) -> dict:
            return {"result": msg.upper()}

        # Register temporary mock tool
        mock_entry = ToolEntry(
            name="__test_mock__",
            description="Test mock",
            input_schema={
                "type": "object",
                "properties": {"msg": {"type": "string"}},
                "required": ["msg"],
            },
            handler=lambda msg: {"result": msg.upper()},
        )
        registry.register(mock_entry)

        resp = client.post(
            "/tools/execute",
            json={"tool_name": "__test_mock__", "inputs": {"msg": "hello"}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["data"]["result"] == "HELLO"
