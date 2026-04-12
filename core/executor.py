"""
core/executor.py
----------------
Central execution engine for MCP tools.

Responsibilities:
- Resolve tool name → handler function via the registry
- Validate inputs against the tool's JSON schema
- Execute the handler with structured error handling
- Return a uniform ToolResponse envelope
- Log every invocation via ToolLogger
"""

from __future__ import annotations

import traceback
from typing import Any, Dict

import jsonschema
from jsonschema import ValidationError

from core.logger import ToolLogger, get_logger
from server.schemas import ToolResponse

log = get_logger(__name__)


class ToolNotFoundError(Exception):
    """Raised when the requested tool name is not registered."""


class InputValidationError(Exception):
    """Raised when tool inputs fail JSON-schema validation."""


class ToolExecutor:
    """
    Executes a registered tool by name, validating inputs first.

    This class is intentionally thin — it delegates all domain logic
    to the individual tool handlers registered in ToolRegistry.
    """

    def __init__(self, registry: "ToolRegistry") -> None:  # noqa: F821
        self._registry = registry

    def execute(self, tool_name: str, inputs: Dict[str, Any]) -> ToolResponse:
        """
        Validate *inputs* and execute the tool identified by *tool_name*.

        Args:
            tool_name: Registered name of the tool to run.
            inputs:    Raw input dict from the caller.

        Returns:
            ToolResponse with status ``"success"`` or ``"error"``.
        """
        with ToolLogger(tool_name, inputs) as tl:
            try:
                tool_def = self._resolve_tool(tool_name)
                self._validate_inputs(tool_def, inputs)
                result = tool_def.handler(**inputs)
                tl.set_result(result)
                response = ToolResponse(status="success", data=result)
            except ToolNotFoundError as exc:
                log.warning("tool_not_found", tool=tool_name, error=str(exc))
                response = ToolResponse(status="error", error=str(exc))
            except InputValidationError as exc:
                log.warning("input_validation_failed", tool=tool_name, error=str(exc))
                response = ToolResponse(status="error", error=str(exc))
            except Exception as exc:  # pylint: disable=broad-except
                log.error(
                    "tool_execution_error",
                    tool=tool_name,
                    error=str(exc),
                    traceback=traceback.format_exc(),
                )
                response = ToolResponse(status="error", error=str(exc))

        return response

    # ── private helpers ──────────────────────────────────────────────────────

    def _resolve_tool(self, tool_name: str) -> Any:
        tool = self._registry.get(tool_name)
        if tool is None:
            raise ToolNotFoundError(
                f"Tool '{tool_name}' is not registered. "
                f"Available tools: {self._registry.list_names()}"
            )
        return tool

    @staticmethod
    def _validate_inputs(tool_def: Any, inputs: Dict[str, Any]) -> None:
        try:
            jsonschema.validate(instance=inputs, schema=tool_def.input_schema)
        except ValidationError as exc:
            raise InputValidationError(
                f"Input validation failed for tool '{tool_def.name}': {exc.message}"
            ) from exc
