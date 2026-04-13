"""
tests/test_tools_terraform.py
------------------------------
Unit tests for Terraform tool handlers (plan / apply / destroy).

TerraformRunner is mocked at the handler level — no real Terraform binary.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


SUCCESS_RESULT = {"stdout": "No changes.", "stderr": "", "exit_code": 0}
CHANGES_RESULT = {"stdout": "Plan: 2 to add.", "stderr": "", "exit_code": 2}
ERROR_RESULT = {"stdout": "", "stderr": "Error: missing provider", "exit_code": 1}


# ── terraform_plan ────────────────────────────────────────────────────────────

class TestTerraformPlanHandler:
    @patch("tools.terraform.plan.TerraformRunner")
    def test_plan_no_changes(self, MockRunner, tmp_path):
        MockRunner.return_value.plan.return_value = SUCCESS_RESULT
        from tools.terraform.plan import handler
        result = handler(path=str(tmp_path))
        assert result["exit_code"] == 0
        assert result["has_changes"] is False
        assert result["dry_run"] is False

    @patch("tools.terraform.plan.TerraformRunner")
    def test_plan_with_changes(self, MockRunner, tmp_path):
        MockRunner.return_value.plan.return_value = CHANGES_RESULT
        from tools.terraform.plan import handler
        result = handler(path=str(tmp_path))
        assert result["exit_code"] == 2
        assert result["has_changes"] is True

    @patch("tools.terraform.plan.TerraformRunner")
    def test_dry_run_calls_validate_not_plan(self, MockRunner, tmp_path):
        MockRunner.return_value.validate.return_value = SUCCESS_RESULT
        from tools.terraform.plan import handler
        result = handler(path=str(tmp_path), dry_run=True)
        MockRunner.return_value.validate.assert_called_once()
        MockRunner.return_value.plan.assert_not_called()
        assert result["dry_run"] is True

    @patch("tools.terraform.plan.get_settings")
    @patch("tools.terraform.plan.TerraformRunner")
    def test_global_dry_run_overrides_false(self, MockRunner, MockSettings, tmp_path):
        """If DRY_RUN=true in config, even dry_run=False should use validate."""
        mock_settings = MagicMock()
        mock_settings.dry_run = True
        MockSettings.return_value = mock_settings
        MockRunner.return_value.validate.return_value = SUCCESS_RESULT
        from tools.terraform.plan import handler
        result = handler(path=str(tmp_path), dry_run=False)
        MockRunner.return_value.validate.assert_called_once()
        assert result["dry_run"] is True


# ── terraform_apply ───────────────────────────────────────────────────────────

class TestTerraformApplyHandler:
    @patch("tools.terraform.apply.TerraformRunner")
    @patch("tools.terraform.apply.get_settings")
    def test_apply_blocked_in_dry_run(self, MockSettings, MockRunner, tmp_path):
        mock_settings = MagicMock()
        mock_settings.dry_run = True
        MockSettings.return_value = mock_settings
        from tools.terraform.apply import handler
        result = handler(path=str(tmp_path))
        assert result["status"] == "blocked"
        assert "DRY_RUN" in result["reason"]
        MockRunner.return_value.apply.assert_not_called()

    @patch("tools.terraform.apply.TerraformRunner")
    @patch("tools.terraform.apply.get_settings")
    def test_apply_without_auto_approve(self, MockSettings, MockRunner, tmp_path):
        mock_settings = MagicMock()
        mock_settings.dry_run = False
        MockSettings.return_value = mock_settings
        MockRunner.return_value.apply.return_value = SUCCESS_RESULT
        from tools.terraform.apply import handler
        result = handler(path=str(tmp_path), auto_approve=False)
        MockRunner.return_value.apply.assert_called_once_with(
            str(tmp_path), auto_approve=False
        )

    @patch("tools.terraform.apply.TerraformRunner")
    @patch("tools.terraform.apply.get_settings")
    def test_apply_with_auto_approve(self, MockSettings, MockRunner, tmp_path):
        mock_settings = MagicMock()
        mock_settings.dry_run = False
        MockSettings.return_value = mock_settings
        MockRunner.return_value.apply.return_value = SUCCESS_RESULT
        from tools.terraform.apply import handler
        handler(path=str(tmp_path), auto_approve=True)
        MockRunner.return_value.apply.assert_called_once_with(
            str(tmp_path), auto_approve=True
        )


# ── terraform_destroy ─────────────────────────────────────────────────────────

class TestTerraformDestroyHandler:
    @patch("tools.terraform.destroy.TerraformRunner")
    @patch("tools.terraform.destroy.get_settings")
    def test_destroy_requires_confirmation(self, MockSettings, MockRunner, tmp_path):
        mock_settings = MagicMock()
        mock_settings.dry_run = False
        MockSettings.return_value = mock_settings
        from tools.terraform.destroy import handler
        result = handler(path=str(tmp_path), confirm_destroy="wrong-string")
        assert result["status"] == "blocked"
        assert "DESTROY" in result["reason"]
        MockRunner.return_value.destroy.assert_not_called()

    @patch("tools.terraform.destroy.TerraformRunner")
    @patch("tools.terraform.destroy.get_settings")
    def test_destroy_proceeds_with_correct_confirmation(self, MockSettings, MockRunner, tmp_path):
        mock_settings = MagicMock()
        mock_settings.dry_run = False
        MockSettings.return_value = mock_settings
        MockRunner.return_value.destroy.return_value = SUCCESS_RESULT
        from tools.terraform.destroy import handler
        result = handler(path=str(tmp_path), confirm_destroy="DESTROY")
        MockRunner.return_value.destroy.assert_called_once()

    @patch("tools.terraform.destroy.TerraformRunner")
    @patch("tools.terraform.destroy.get_settings")
    def test_destroy_blocked_in_dry_run(self, MockSettings, MockRunner, tmp_path):
        mock_settings = MagicMock()
        mock_settings.dry_run = True
        MockSettings.return_value = mock_settings
        from tools.terraform.destroy import handler
        result = handler(path=str(tmp_path), confirm_destroy="DESTROY")
        assert result["status"] == "blocked"
        MockRunner.return_value.destroy.assert_not_called()


# ── TerraformRunner extended path validation ──────────────────────────────────

class TestTerraformRunnerExtended:
    @pytest.fixture
    def runner(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TERRAFORM_ALLOWED_BASE_DIR", str(tmp_path))
        from core.config import get_settings
        get_settings.cache_clear()
        from integrations.terraform_runner import TerraformRunner
        return TerraformRunner()

    def test_symlink_escape_blocked(self, runner, tmp_path):
        """Symlink pointing outside allowed base must be blocked."""
        from integrations.terraform_runner import TerraformPathError
        import os
        outside = tmp_path.parent / "outside"
        outside.mkdir(exist_ok=True)
        link = tmp_path / "evil_link"
        os.symlink(str(outside), str(link))
        with pytest.raises(TerraformPathError, match="outside the allowed"):
            runner._validated_path(str(link))

    def test_file_not_directory_raises(self, runner, tmp_path):
        from integrations.terraform_runner import TerraformPathError
        f = tmp_path / "not_a_dir.tf"
        f.write_text("resource {}")
        with pytest.raises(TerraformPathError, match="not a directory"):
            runner._validated_path(str(f))

    def test_timeout_triggers_run_error(self, runner, tmp_path):
        import subprocess
        from integrations.terraform_runner import TerraformRunError
        work_dir = tmp_path / "infra"
        work_dir.mkdir()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("terraform", 60)):
            with pytest.raises(TerraformRunError, match="timed out"):
                runner._run(["plan"], work_dir)

    def test_concurrent_path_lock_serializes(self, runner, tmp_path):
        """Two threads targeting the same path must serialize via the lock."""
        import threading
        from integrations.terraform_runner import _get_path_lock
        work_dir = tmp_path / "concurrent"
        work_dir.mkdir()

        lock = _get_path_lock(work_dir)
        results = []

        def acquire_and_release():
            with lock:
                results.append("acquired")

        threads = [threading.Thread(target=acquire_and_release) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 5  # all got through, serially
