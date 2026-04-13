"""
tests/test_executor.py
-----------------------
Unit tests for ToolExecutor.

execute()      raises ToolNotFoundError / InputValidationError — callers
               must handle these (HTTP layer converts to 404/400).
execute_safe() catches all errors and returns ToolResponse(status='error').
"""

from __future__ import annotations

import pytest

from core.executor import InputValidationError, ToolExecutor, ToolNotFoundError
from server.registry import ToolEntry, ToolRegistry
from server.schemas import ToolResponse


# ── Fixtures ──────────────────────────────────────────────────────────────────

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
        "additionalProperties": False,
    },
    handler=_echo_handler,
)

FAILING_ENTRY = ToolEntry(
    name="failing",
    description="Always fails",
    input_schema={"type": "object", "properties": {}},
    handler=_failing_handler,
)


@pytest.fixture
def executor():
    registry = ToolRegistry()
    registry.register(ECHO_ENTRY)
    registry.register(FAILING_ENTRY)
    return ToolExecutor(registry)


# ── execute() — raises on bad tool / bad input ────────────────────────────────

class TestExecuteStrict:
    def test_success_returns_tool_response(self, executor):
        resp = executor.execute("echo", {"message": "hello"})
        assert isinstance(resp, ToolResponse)
        assert resp.status == "success"
        assert resp.data == {"echo": "hello"}
        assert resp.error is None

    def test_unknown_tool_raises_tool_not_found(self, executor):
        with pytest.raises(ToolNotFoundError, match="not registered"):
            executor.execute("nonexistent", {})

    def test_missing_required_field_raises_input_validation(self, executor):
        with pytest.raises(InputValidationError, match="'message' is a required property"):
            executor.execute("echo", {})

    def test_wrong_type_raises_input_validation(self, executor):
        with pytest.raises(InputValidationError, match="is not of type"):
            executor.execute("echo", {"message": 123})

    def test_extra_properties_blocked(self, executor):
        with pytest.raises(InputValidationError, match="Additional properties"):
            executor.execute("echo", {"message": "hi", "extra_key": "bad"})

    def test_handler_runtime_error_returned_as_error_response(self, executor):
        """Runtime errors from the handler itself are caught and returned, not raised."""
        resp = executor.execute("failing", {})
        assert resp.status == "error"
        assert "intentional failure" in resp.error

    def test_success_result_has_no_error(self, executor):
        resp = executor.execute("echo", {"message": "test"})
        assert resp.error is None
        assert resp.data is not None


# ── execute_safe() — never raises, always ToolResponse ───────────────────────

class TestExecuteSafe:
    def test_success_path(self, executor):
        resp = executor.execute_safe("echo", {"message": "safe"})
        assert resp.status == "success"
        assert resp.data == {"echo": "safe"}

    def test_unknown_tool_returns_error_response(self, executor):
        resp = executor.execute_safe("nonexistent", {})
        assert resp.status == "error"
        assert "not registered" in resp.error

    def test_invalid_input_returns_error_response(self, executor):
        resp = executor.execute_safe("echo", {})
        assert resp.status == "error"
        assert "message" in resp.error

    def test_handler_failure_returns_error_response(self, executor):
        resp = executor.execute_safe("failing", {})
        assert resp.status == "error"
        assert "intentional failure" in resp.error

    def test_never_raises(self, executor):
        """execute_safe must never raise under any circumstance."""
        for bad_input in [{}, {"message": 123}, {"x": "y"}]:
            resp = executor.execute_safe("echo", bad_input)
            assert resp.status == "error"
