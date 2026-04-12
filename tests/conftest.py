"""
tests/conftest.py
-----------------
Shared pytest fixtures for the devops_mcp test suite.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.registry import build_registry
from core.executor import ToolExecutor


@pytest.fixture(scope="session")
def registry():
    """Session-scoped registry — build once for all tests."""
    return build_registry()


@pytest.fixture(scope="session")
def executor(registry):
    return ToolExecutor(registry)


@pytest.fixture(scope="session")
def api_client(registry):
    """FastAPI TestClient with the real registry (no live AWS/GitHub calls)."""
    # Import here to avoid circular import at module level
    from server.main import app
    return TestClient(app)
