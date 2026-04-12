"""
tests/test_terraform_runner.py
-------------------------------
Unit tests for TerraformRunner path validation and subprocess safety.
No real Terraform binary is called.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from integrations.terraform_runner import TerraformPathError, TerraformRunner


@pytest.fixture
def runner(tmp_path, monkeypatch):
    """
    Return a TerraformRunner with TERRAFORM_ALLOWED_BASE_DIR set to tmp_path.
    """
    monkeypatch.setenv("TERRAFORM_ALLOWED_BASE_DIR", str(tmp_path))
    # Clear the lru_cache so settings pick up the monkeypatched env var
    from core.config import get_settings
    get_settings.cache_clear()
    return TerraformRunner()


class TestPathValidation:
    def test_valid_path_inside_base(self, runner, tmp_path):
        work_dir = tmp_path / "infra"
        work_dir.mkdir()
        resolved = runner._validated_path(str(work_dir))
        assert resolved == work_dir.resolve()

    def test_path_outside_base_raises(self, runner, tmp_path):
        with pytest.raises(TerraformPathError, match="outside the allowed"):
            runner._validated_path("/etc")

    def test_nonexistent_path_raises(self, runner, tmp_path):
        with pytest.raises(TerraformPathError):
            runner._validated_path(str(tmp_path / "does_not_exist"))

    def test_path_traversal_blocked(self, runner, tmp_path):
        """Ensure ../../../etc style traversal is blocked."""
        evil_path = str(tmp_path / "infra" / ".." / ".." / "etc")
        with pytest.raises(TerraformPathError):
            runner._validated_path(evil_path)


class TestRunMethod:
    def test_file_not_found_raises_runtime_error(self, runner, tmp_path):
        from integrations.terraform_runner import TerraformRunError
        work_dir = tmp_path / "infra"
        work_dir.mkdir()

        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(TerraformRunError, match="not found"):
                runner._run(["plan"], work_dir)

    def test_successful_run_returns_dict(self, runner, tmp_path):
        work_dir = tmp_path / "infra"
        work_dir.mkdir()

        mock_result = MagicMock()
        mock_result.stdout = "No changes."
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = runner._run(["plan"], work_dir)

        assert result["stdout"] == "No changes."
        assert result["exit_code"] == 0
