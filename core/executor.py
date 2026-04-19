"""
core/executor.py
----------------
Central execution engine for MCP tools.

Responsibilities:
- Resolve tool name → handler function via the registry
- Validate inputs against the tool's JSON schema
- Execute the handler with a per-tool timeout (ThreadPoolExecutor)
- Record every call in the SQLite audit log
- Post Slack notifications on success or failure
- Return a uniform ToolResponse envelope
- Log every invocation via ToolLogger
"""

from __future__ import annotations

import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Dict, Optional

import jsonschema
from jsonschema import ValidationError

from core.audit import audit_log
from core.config import get_settings
from core.logger import ToolLogger, get_logger
from integrations.slack_client import slack_notify
from server.schemas import ToolResponse

log = get_logger(__name__)

# Shared thread pool for tool execution with timeout support
_executor_pool = ThreadPoolExecutor(max_workers=20, thread_name_prefix="mcp-tool")


class ToolNotFoundError(Exception):
    """Raised when the requested tool name is not registered."""


class InputValidationError(Exception):
    """Raised when tool inputs fail JSON-schema validation."""


class ToolTimeoutError(Exception):
    """Raised when a tool exceeds its execution timeout."""


class ToolExecutor:
    """
    Executes a registered tool by name, validating inputs first.

    Features:
    - Per-tool configurable timeout (falls back to TOOL_TIMEOUT_SECONDS)
    - SQLite audit log for every invocation
    - Slack notifications on success and failure
    - Uniform ToolResponse envelope
    """

    def __init__(self, registry: "ToolRegistry") -> None:  # noqa: F821
        self._registry = registry

    def execute(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        api_key_hint: str = "anonymous",
    ) -> ToolResponse:
        """
        Validate *inputs* and execute the tool identified by *tool_name*.

        Raises:
            ToolNotFoundError:   if the tool name is not registered.
            InputValidationError: if inputs fail JSON-schema validation.
            ToolTimeoutError:    if execution exceeds the configured timeout.

        Returns:
            ToolResponse with status ``"success"`` or ``"error"`` for
            runtime errors from the tool itself (e.g. AWS API failures).
        """
        with ToolLogger(tool_name, inputs) as tl:
            tool_def = self._resolve_tool(tool_name)
            self._validate_inputs(tool_def, inputs)

            timeout = self._get_timeout(tool_def)
            t_start = time.monotonic()

            try:
                result = self._run_with_timeout(tool_def, inputs, timeout)
                duration_ms = int((time.monotonic() - t_start) * 1000)
                tl.set_result(result)

                audit_log.record(
                    tool_name=tool_name,
                    status="success",
                    duration_ms=duration_ms,
                    api_key_hint=api_key_hint,
                    inputs=inputs,
                )

                response = ToolResponse(status="success", data=result)

            except ToolTimeoutError as exc:
                duration_ms = int((time.monotonic() - t_start) * 1000)
                error_msg = str(exc)
                log.error("tool_timeout", tool=tool_name, timeout_s=timeout)
                audit_log.record(
                    tool_name=tool_name,
                    status="error",
                    duration_ms=duration_ms,
                    api_key_hint=api_key_hint,
                    inputs=inputs,
                    error=error_msg,
                )
                slack_notify.tool_failure(tool_name, inputs, error_msg, duration_ms)
                response = ToolResponse(status="error", error=error_msg)

            except Exception as exc:  # pylint: disable=broad-except
                duration_ms = int((time.monotonic() - t_start) * 1000)
                error_msg = str(exc)
                log.error(
                    "tool_execution_error",
                    tool=tool_name,
                    error=error_msg,
                    traceback=traceback.format_exc(),
                )
                audit_log.record(
                    tool_name=tool_name,
                    status="error",
                    duration_ms=duration_ms,
                    api_key_hint=api_key_hint,
                    inputs=inputs,
                    error=error_msg,
                )
                slack_notify.tool_failure(tool_name, inputs, error_msg, duration_ms)
                response = ToolResponse(status="error", error=error_msg)

        return response

    def execute_safe(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        api_key_hint: str = "anonymous",
    ) -> ToolResponse:
        """
        Like ``execute`` but catches all exceptions (including ToolNotFoundError
        and InputValidationError) and returns them as error ToolResponses.

        Used by the batch endpoint and background job runner so one bad call
        never aborts the whole batch.
        """
        try:
            return self.execute(tool_name, inputs, api_key_hint)
        except (ToolNotFoundError, InputValidationError) as exc:
            log.warning("tool_call_error", tool=tool_name, error=str(exc))
            return ToolResponse(status="error", error=str(exc))
        except Exception as exc:
            log.error("tool_call_error", tool=tool_name, error=str(exc))
            return ToolResponse(status="error", error=str(exc))

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

    @staticmethod
    def _get_timeout(tool_def: Any) -> Optional[int]:
        """Return timeout in seconds. None means no timeout."""
        # Per-tool override takes priority, then global setting
        per_tool: Optional[int] = getattr(tool_def, "timeout_seconds", None)
        if per_tool is not None:
            return per_tool if per_tool > 0 else None
        global_timeout = get_settings().default_tool_timeout_seconds
        return global_timeout if global_timeout > 0 else None

    @staticmethod
    def _run_with_timeout(tool_def: Any, inputs: Dict[str, Any], timeout: Optional[int]) -> Any:
        """Submit the tool handler to the thread pool with an optional timeout.

        NOTE: future.cancel() cannot stop a thread that is already running —
        Python threads are not interruptible. The future is abandoned (its result
        is ignored) but the underlying thread continues until the tool finishes or
        the process exits. For subprocess-based tools (Terraform) the subprocess
        itself will be killed by the OS when the timeout is hit at the subprocess
        layer (see TerraformRunner._run → subprocess.run(timeout=...)), so the
        effective cancellation happens there, not here.
        """
        future = _executor_pool.submit(tool_def.handler, **inputs)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            # Do not call future.cancel() — it is a no-op for running threads and
            # misleadingly implies the work stopped. We simply stop waiting.
            raise ToolTimeoutError(
                f"Tool '{tool_def.name}' exceeded its {timeout}s timeout. "
                "The underlying operation may still be running to completion."
            )
