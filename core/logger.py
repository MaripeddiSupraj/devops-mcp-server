"""
core/logger.py
--------------
Structured JSON logging setup for the entire application.
Provides a `get_logger` factory and a context-aware `ToolLogger` wrapper
that automatically includes tool name, inputs, timing, and errors.
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from typing import Any, Dict, Generator

import structlog
from structlog.types import FilteringBoundLogger

from core.config import get_settings


def _configure_structlog() -> None:
    """Configure structlog once at import time."""
    settings = get_settings()

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if sys.stdout.isatty():
        # Human-readable output for local development
        renderer = structlog.dev.ConsoleRenderer()
    else:
        # Machine-parseable JSON in CI / production
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also route stdlib logging through structlog so third-party libs are captured
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.getLevelName(settings.log_level.upper()),
    )


_configure_structlog()


def get_logger(name: str) -> FilteringBoundLogger:
    """Return a structlog logger bound to *name*."""
    return structlog.get_logger(name)


class ToolLogger:
    """
    Context manager that logs tool invocation lifecycle.

    Usage::

        with ToolLogger("terraform_plan", inputs={"path": "/infra"}) as tl:
            result = run_something()
            tl.set_result(result)
    """

    def __init__(self, tool_name: str, inputs: Dict[str, Any]) -> None:
        self._log = get_logger(tool_name)
        self._tool_name = tool_name
        self._inputs = inputs
        self._start: float = 0.0

    def __enter__(self) -> "ToolLogger":
        self._start = time.perf_counter()
        self._log.info(
            "tool_invoked",
            tool=self._tool_name,
            inputs=self._inputs,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        elapsed_ms = round((time.perf_counter() - self._start) * 1000, 2)
        if exc_type:
            self._log.error(
                "tool_failed",
                tool=self._tool_name,
                elapsed_ms=elapsed_ms,
                error=str(exc_val),
                exc_info=(exc_type, exc_val, exc_tb),
            )
        else:
            self._log.info(
                "tool_completed",
                tool=self._tool_name,
                elapsed_ms=elapsed_ms,
            )
        return False  # do not suppress exceptions

    def set_result(self, result: Any) -> None:
        """Optionally bind a result summary for richer log output."""
        self._log = self._log.bind(result_preview=str(result)[:200])
