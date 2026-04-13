"""
tests/test_security.py
-----------------------
Tests for API key authentication (core/security.py).

Strategy: mock get_settings() directly in each test to avoid
lru_cache ordering issues across fixtures. This makes each test
self-contained and deterministic.
"""

from __future__ import annotations

import hmac
import inspect
import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def _make_settings(api_key=None):
    s = MagicMock()
    s.api_key = api_key
    return s


def _client(api_key=None, headers=None):
    """Build a fresh TestClient where get_settings returns a controlled value."""
    from server.main import app
    c = TestClient(app, raise_server_exceptions=False, headers=headers or {})
    return c


# ── Auth disabled (no API key configured) ────────────────────────────────────

class TestAuthDisabled:
    def test_execute_passes_without_any_key(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key=None)):
            c = _client()
            r = c.post("/tools/execute", json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert r.status_code == 200  # tool ran (errored due to no cluster, but 200 OK)

    def test_batch_passes_without_key(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key=None)):
            c = _client()
            r = c.post("/tools/execute/batch",
                       json={"calls": [{"tool_name": "k8s_get_pods", "inputs": {}}]})
        assert r.status_code == 200

    def test_health_always_public_regardless_of_key_config(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key="secret")):
            c = _client()
            # Health endpoints don't use verify_api_key dependency
            assert c.get("/health/live").status_code == 200

    def test_tools_list_always_public(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key="secret")):
            c = _client()
            assert c.get("/tools").status_code == 200


# ── Auth enabled — missing key → 401 ─────────────────────────────────────────

class TestAuthMissingKey:
    def test_execute_without_key_returns_401(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key="secret")):
            c = _client(headers={})  # no key sent
            r = c.post("/tools/execute", json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert r.status_code == 401

    def test_401_response_has_detail(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key="secret")):
            c = _client()
            r = c.post("/tools/execute", json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert "Authentication required" in r.json()["detail"]

    def test_401_response_has_www_authenticate_header(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key="secret")):
            c = _client()
            r = c.post("/tools/execute", json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert "www-authenticate" in r.headers

    def test_batch_without_key_returns_401(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key="secret")):
            c = _client()
            r = c.post("/tools/execute/batch",
                       json={"calls": [{"tool_name": "k8s_get_pods", "inputs": {}}]})
        assert r.status_code == 401

    def test_async_without_key_returns_401(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key="secret")):
            c = _client()
            r = c.post("/tools/execute/async",
                       json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert r.status_code == 401


# ── Auth enabled — wrong key → 403 ───────────────────────────────────────────

class TestAuthWrongKey:
    def test_wrong_x_api_key_returns_403(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key="correct-key")):
            c = _client(headers={"X-API-Key": "wrong-key"})
            r = c.post("/tools/execute", json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert r.status_code == 403

    def test_wrong_bearer_token_returns_403(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key="correct-key")):
            c = _client(headers={"Authorization": "Bearer wrong-key"})
            r = c.post("/tools/execute", json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert r.status_code == 403

    def test_403_detail_message(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key="secret")):
            c = _client(headers={"X-API-Key": "nope"})
            r = c.post("/tools/execute", json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert "Invalid API key" in r.json()["detail"]

    def test_truncated_key_rejected(self):
        """Partial match must be rejected — prevents prefix-guessing attacks."""
        with patch("core.security.get_settings", return_value=_make_settings(api_key="full-secret-key-xyz")):
            c = _client(headers={"X-API-Key": "full-secret-key"})  # truncated
            r = c.post("/tools/execute", json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert r.status_code == 403

    def test_empty_string_key_rejected(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key="secret")):
            c = _client(headers={"X-API-Key": ""})
            r = c.post("/tools/execute", json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert r.status_code in (401, 403)  # empty = missing or invalid


# ── Auth enabled — correct key → passes ──────────────────────────────────────

class TestAuthValidKey:
    def test_correct_x_api_key_passes(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key="my-secret")):
            c = _client(headers={"X-API-Key": "my-secret"})
            r = c.post("/tools/execute", json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert r.status_code == 200

    def test_correct_bearer_token_passes(self):
        with patch("core.security.get_settings", return_value=_make_settings(api_key="my-secret")):
            c = _client(headers={"Authorization": "Bearer my-secret"})
            r = c.post("/tools/execute", json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert r.status_code == 200

    def test_x_api_key_takes_priority_over_bearer(self):
        """When both headers sent, X-API-Key wins."""
        with patch("core.security.get_settings", return_value=_make_settings(api_key="correct")):
            c = _client(headers={"X-API-Key": "correct", "Authorization": "Bearer wrong"})
            r = c.post("/tools/execute", json={"tool_name": "k8s_get_pods", "inputs": {}})
        assert r.status_code == 200


# ── Security implementation checks ───────────────────────────────────────────

class TestSecurityImplementation:
    def test_hmac_compare_digest_used(self):
        """Must use constant-time comparison to prevent timing attacks."""
        from core import security
        source = inspect.getsource(security)
        assert "hmac.compare_digest" in source

    def test_no_string_equality_for_key_comparison(self):
        """Must NOT use == for key comparison."""
        from core import security
        source = inspect.getsource(security)
        # The comparison should not be a simple string == check
        assert "provided == expected" not in source
        assert "expected == provided" not in source

    def test_compare_digest_constant_time(self):
        """Verify hmac.compare_digest behaves correctly for our use-case."""
        assert hmac.compare_digest("correct-key", "correct-key") is True
        assert hmac.compare_digest("correct-key", "wrong-key") is False
        assert hmac.compare_digest("key", "key-longer") is False


# ── Security headers ──────────────────────────────────────────────────────────

class TestSecurityResponseHeaders:
    def test_x_content_type_options_nosniff(self):
        from server.main import app
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/health/live")
        assert r.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options_deny(self):
        from server.main import app
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/health/live")
        assert r.headers.get("x-frame-options") == "DENY"

    def test_referrer_policy_set(self):
        from server.main import app
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/health/live")
        assert r.headers.get("referrer-policy") == "no-referrer"

    def test_x_environment_header_present(self):
        from server.main import app
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/health/live")
        assert "x-environment" in r.headers

    def test_request_id_header_always_present(self):
        from server.main import app
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/health/live")
        assert "x-request-id" in r.headers
