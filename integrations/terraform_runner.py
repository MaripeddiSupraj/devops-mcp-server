"""
integrations/terraform_runner.py
---------------------------------
Low-level wrapper around the Terraform CLI binary.

Security design:
- Only the whitelisted binary path is ever executed.
- The working directory is validated against TERRAFORM_ALLOWED_BASE_DIR.
- No shell=True is used — arguments are passed as a list.
- stderr and stdout are fully captured; the raw process is never exposed.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import List

from core.config import get_settings
from core.logger import get_logger

log = get_logger(__name__)


class TerraformPathError(ValueError):
    """Raised when a Terraform working directory is outside the allowed base."""


class TerraformRunError(RuntimeError):
    """Raised when the Terraform process exits with a non-zero code."""


class TerraformRunner:
    """
    Executes Terraform CLI commands in a validated working directory.

    All public methods return a dict with keys:
        stdout  (str)  – captured standard output
        stderr  (str)  – captured standard error
        exit_code (int)
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._binary = self._settings.terraform_binary
        self._allowed_base = Path(self._settings.terraform_allowed_base_dir).resolve()

    # ── public interface ─────────────────────────────────────────────────────

    def plan(self, path: str, extra_args: List[str] | None = None) -> dict:
        """Run `terraform plan` in *path* and return structured output."""
        work_dir = self._validated_path(path)
        self._ensure_initialized(work_dir)
        args = ["plan", "-no-color", "-detailed-exitcode"] + (extra_args or [])
        return self._run(args, work_dir)

    def apply(self, path: str, auto_approve: bool = False) -> dict:
        """Run `terraform apply` in *path*.

        Args:
            path:         Terraform working directory (must be under allowed base).
            auto_approve: Pass ``-auto-approve`` flag (disabled by default for safety).
        """
        work_dir = self._validated_path(path)
        self._ensure_initialized(work_dir)
        args = ["apply", "-no-color"]
        if auto_approve:
            args.append("-auto-approve")
        return self._run(args, work_dir)

    def destroy(self, path: str, auto_approve: bool = False) -> dict:
        """Run `terraform destroy` in *path*."""
        work_dir = self._validated_path(path)
        self._ensure_initialized(work_dir)
        args = ["destroy", "-no-color"]
        if auto_approve:
            args.append("-auto-approve")
        return self._run(args, work_dir)

    def version(self) -> dict:
        """Return `terraform version` output."""
        return self._run(["version", "-json"], cwd=None)

    # ── private helpers ───────────────────────────────────────────────────────

    def _validated_path(self, path: str) -> Path:
        """
        Resolve *path* and verify it sits inside the allowed base directory.

        Raises:
            TerraformPathError: if the path escapes the allowed base.
        """
        resolved = Path(path).resolve()
        try:
            resolved.relative_to(self._allowed_base)
        except ValueError:
            raise TerraformPathError(
                f"Path '{resolved}' is outside the allowed Terraform base "
                f"directory '{self._allowed_base}'. "
                "Set TERRAFORM_ALLOWED_BASE_DIR to change the allowed root."
            )
        if not resolved.is_dir():
            raise TerraformPathError(f"Path '{resolved}' does not exist or is not a directory.")
        return resolved

    def _ensure_initialized(self, work_dir: Path) -> None:
        """Run `terraform init` if the .terraform directory is missing."""
        terraform_dir = work_dir / ".terraform"
        if not terraform_dir.exists():
            log.info("terraform_init_required", path=str(work_dir))
            result = self._run(["init", "-no-color", "-input=false"], work_dir)
            if result["exit_code"] != 0:
                raise TerraformRunError(
                    f"terraform init failed:\n{result['stderr']}"
                )

    def _run(self, args: List[str], cwd: Path | None) -> dict:
        """
        Execute the Terraform binary with *args* in *cwd*.

        Never uses shell=True. stderr/stdout are fully captured.
        """
        cmd = [self._binary] + args
        log.debug("terraform_exec", cmd=cmd, cwd=str(cwd) if cwd else None)

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                timeout=600,  # 10-minute safety timeout
            )
        except FileNotFoundError:
            raise TerraformRunError(
                f"Terraform binary '{self._binary}' not found. "
                "Install Terraform and ensure it is on PATH."
            )
        except subprocess.TimeoutExpired:
            raise TerraformRunError("Terraform command timed out after 600 seconds.")

        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
        }
