"""
tests/test_startup.py
----------------------
Unit tests for core/startup.py — credential and configuration checks.

Each check is tested in isolation using a minimal Settings object.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

from core.startup import (
    _check_aws,
    _check_github,
    _check_kubeconfig,
    _check_terraform,
    collect_startup_warnings,
)


def _settings(**kwargs):
    """Build a minimal Settings-like object for testing."""
    from core.config import Settings
    # Use construct to bypass validation so we can set any combination
    defaults = dict(
        github_token=None,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_region="us-east-1",
        kubeconfig_path=None,
        terraform_binary="terraform",
        terraform_allowed_base_dir="/tmp/terraform",
        terraform_timeout_seconds=600,
        server_host="0.0.0.0",
        server_port=8000,
        log_level="INFO",
        dry_run=False,
        api_key=None,
        environment="development",
        cors_origins="*",
    )
    defaults.update(kwargs)
    return Settings.model_construct(**defaults)


# ── GitHub checks ──────────────────────────────────────────────────────────────

class TestCheckGitHub:
    def test_no_token_returns_warning(self):
        w = _check_github(_settings(github_token=None))
        assert w is not None
        assert "GITHUB_TOKEN" in w

    def test_token_set_returns_none(self):
        w = _check_github(_settings(github_token="ghp_test"))
        assert w is None


# ── AWS checks ────────────────────────────────────────────────────────────────

class TestCheckAWS:
    def test_neither_key_set_warns(self):
        w = _check_aws(_settings(aws_access_key_id=None, aws_secret_access_key=None))
        assert w is not None
        assert "AWS_ACCESS_KEY_ID" in w

    def test_only_key_id_set_warns(self):
        w = _check_aws(_settings(aws_access_key_id="AKID", aws_secret_access_key=None))
        assert w is not None
        assert "both" in w.lower()

    def test_only_secret_set_warns(self):
        w = _check_aws(_settings(aws_access_key_id=None, aws_secret_access_key="secret"))
        assert w is not None

    def test_both_set_returns_none(self):
        w = _check_aws(_settings(aws_access_key_id="AKID", aws_secret_access_key="SECRET"))
        assert w is None


# ── Kubeconfig checks ─────────────────────────────────────────────────────────

class TestCheckKubeconfig:
    def test_no_kubeconfig_warns(self):
        w = _check_kubeconfig(_settings(kubeconfig_path=None))
        assert w is not None
        assert "KUBECONFIG" in w

    def test_path_not_existing_warns(self, tmp_path):
        missing = str(tmp_path / "nonexistent" / "config")
        w = _check_kubeconfig(_settings(kubeconfig_path=missing))
        assert w is not None
        assert "does not exist" in w

    def test_valid_path_returns_none(self, tmp_path):
        kube = tmp_path / "config"
        kube.write_text("apiVersion: v1")
        w = _check_kubeconfig(_settings(kubeconfig_path=str(kube)))
        assert w is None


# ── Terraform checks ──────────────────────────────────────────────────────────

class TestCheckTerraform:
    def test_binary_not_on_path_warns(self):
        with patch("shutil.which", return_value=None):
            w = _check_terraform(_settings(terraform_binary="terraform"))
        assert w is not None
        assert "not found on PATH" in w

    def test_binary_on_path_returns_none(self):
        with patch("shutil.which", return_value="/usr/local/bin/terraform"):
            w = _check_terraform(_settings(terraform_binary="terraform"))
        assert w is None


# ── collect_startup_warnings ──────────────────────────────────────────────────

class TestCollectStartupWarnings:
    def test_all_missing_returns_multiple_warnings(self):
        with patch("shutil.which", return_value=None):
            warnings = collect_startup_warnings(_settings())
        assert len(warnings) >= 3  # github, aws, kubeconfig, terraform

    def test_all_set_returns_empty_list(self, tmp_path):
        kube = tmp_path / "config"
        kube.write_text("apiVersion: v1")
        s = _settings(
            github_token="ghp_x",
            aws_access_key_id="AKID",
            aws_secret_access_key="SECRET",
            kubeconfig_path=str(kube),
        )
        with patch("shutil.which", return_value="/usr/bin/terraform"):
            warnings = collect_startup_warnings(s)
        assert warnings == []

    def test_warnings_are_strings(self):
        with patch("shutil.which", return_value=None):
            warnings = collect_startup_warnings(_settings())
        for w in warnings:
            assert isinstance(w, str)
            assert len(w) > 0

    def test_partial_config_warns_only_for_missing(self, tmp_path):
        """Only the missing piece shows a warning."""
        kube = tmp_path / "config"
        kube.write_text("apiVersion: v1")
        s = _settings(
            github_token="ghp_x",
            aws_access_key_id="AKID",
            aws_secret_access_key="SECRET",
            kubeconfig_path=str(kube),
            terraform_binary="terraform",
        )
        with patch("shutil.which", return_value=None):  # terraform missing
            warnings = collect_startup_warnings(s)
        assert len(warnings) == 1
        assert "terraform" in warnings[0].lower()
