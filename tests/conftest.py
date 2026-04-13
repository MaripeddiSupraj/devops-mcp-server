"""
tests/conftest.py
-----------------
Shared pytest fixtures for the devops_mcp test suite.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def registry():
    from server.registry import build_registry
    return build_registry()


@pytest.fixture(scope="session")
def executor(registry):
    from core.executor import ToolExecutor
    return ToolExecutor(registry)


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient — no live external calls, auth disabled."""
    from server.main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="session")
def authed_client():
    """TestClient with API key header pre-set (for auth tests)."""
    import os
    os.environ["MCP_API_KEY"] = "test-secret-key"
    from core.config import get_settings
    get_settings.cache_clear()
    from server.main import app
    c = TestClient(app, raise_server_exceptions=False, headers={"X-API-Key": "test-secret-key"})
    yield c
    del os.environ["MCP_API_KEY"]
    get_settings.cache_clear()
