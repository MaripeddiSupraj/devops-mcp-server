"""
tests/test_executor.py
-----------------------
Unit tests for ToolExecutor — covers success path, unknown tool,
input validation failure, and runtime exceptions.
"""

from __future__ import annotations

import pytest

from core.executor import ToolExecutor
from server.registry import ToolEntry, ToolRegistry


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_registry(*entries: ToolEntry) -> ToolRegistry:
    registry = ToolRegistry()
    for entry in entries:
        registry.register(entry)
    return registry


def _echo_handler(message: str) -> dict:
    return {"echo": message}


def _failing_handler(**kwargs):
    raise RuntimeError("intentional failure")


ECHO_ENTRY = ToolEntry(
    name="echo",
    description="Echoes a message",
    input_schema={
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    },
    handler=_echo_handler,
)

FAILING_ENTRY = ToolEntry(
    name="failing",
    description="Always fails",
    input_schema={"type": "object", "properties": {}},
    handler=_failing_handler,
)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestToolExecutor:
    def setup_method(self):
        registry = _make_registry(ECHO_ENTRY, FAILING_ENTRY)
        self.executor = ToolExecutor(registry)

    def test_success_path(self):
        response = self.executor.execute("echo", {"message": "hello"})
        assert response.status == "success"
        assert response.data == {"echo": "hello"}
        assert response.error is None

    def test_unknown_tool(self):
        response = self.executor.execute("nonexistent", {})
        assert response.status == "error"
        assert "not registered" in response.error

    def test_missing_required_input(self):
        response = self.executor.execute("echo", {})   # missing 'message'
        assert response.status == "error"
        assert "validation" in response.error.lower()

    def test_wrong_input_type(self):
        response = self.executor.execute("echo", {"message": 123})  # should be string
        assert response.status == "error"

    def test_handler_exception_caught(self):
        response = self.executor.execute("failing", {})
        assert response.status == "error"
        assert "intentional failure" in response.error
