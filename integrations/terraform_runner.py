"""
integrations/terraform_runner.py
---------------------------------
Low-level wrapper around the Terraform CLI binary.

Security design:
- Only the whitelisted binary path is ever executed.
- The working directory is validated against TERRAFORM_ALLOWED_BASE_DIR.
- Symlinks are fully resolved before the base-dir check (prevents escape attacks).
- No shell=True is used — arguments are passed as a list.
- stderr and stdout are fully captured; the raw process is never exposed.

Concurrency design:
- A per-path threading.Lock prevents two concurrent calls from corrupting
  the same Terraform working directory (state, plan files, .terraform/).
- The global _LOCKS_MUTEX guards the lock registry itself.

Configuration:
- TERRAFORM_TIMEOUT_SECONDS controls how long any single command may run.
"""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Dict, List

from core.config import get_settings
from core.logger import get_logger

log = get_logger(__name__)

# ── Per-path lock registry ────────────────────────────────────────────────────

_LOCKS: Dict[str, threading.Lock] = {}
_LOCKS_MUTEX = threading.Lock()


def _get_path_lock(path: Path) -> threading.Lock:
    """
    Return (and lazily create) a per-path Lock.

    Two concurrent tool calls targeting the same Terraform directory will
    serialise here instead of racing on state files.
    """
    key = str(path)
    with _LOCKS_MUTEX:
        if key not in _LOCKS:
            _LOCKS[key] = threading.Lock()
        return _LOCKS[key]


# ── Exceptions ────────────────────────────────────────────────────────────────

class TerraformPathError(ValueError):
    """Raised when a Terraform working directory is outside the allowed base."""


class TerraformRunError(RuntimeError):
    """Raised when the Terraform process exits with a non-zero code."""


# ── Runner ────────────────────────────────────────────────────────────────────

class TerraformRunner:
    """
    Executes Terraform CLI commands in a validated working directory.

    All public methods return a dict with keys:
        stdout    (str)  – captured standard output
        stderr    (str)  – captured standard error
        exit_code (int)
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._binary = self._settings.terraform_binary
        self._allowed_base = Path(self._settings.terraform_allowed_base_dir).resolve()
        self._timeout = self._settings.terraform_timeout_seconds

    # ── public interface ─────────────────────────────────────────────────────

    def plan(self, path: str, extra_args: List[str] | None = None) -> dict:
        """Run ``terraform plan`` in *path* and return structured output."""
        work_dir = self._validated_path(path)
        with _get_path_lock(work_dir):
            self._ensure_initialized(work_dir)
            args = ["plan", "-no-color", "-detailed-exitcode"] + (extra_args or [])
            return self._run(args, work_dir)

    def apply(self, path: str, auto_approve: bool = False) -> dict:
        """
        Run ``terraform apply`` in *path*.

        Args:
            path:         Terraform working directory (must be under allowed base).
            auto_approve: Pass ``-auto-approve`` flag (disabled by default for safety).
        """
        work_dir = self._validated_path(path)
        with _get_path_lock(work_dir):
            self._ensure_initialized(work_dir)
            args = ["apply", "-no-color"]
            if auto_approve:
                args.append("-auto-approve")
            return self._run(args, work_dir)

    def destroy(self, path: str, auto_approve: bool = False) -> dict:
        """Run ``terraform destroy`` in *path*."""
        work_dir = self._validated_path(path)
        with _get_path_lock(work_dir):
            self._ensure_initialized(work_dir)
            args = ["destroy", "-no-color"]
            if auto_approve:
                args.append("-auto-approve")
            return self._run(args, work_dir)

    def version(self) -> dict:
        """Return ``terraform version`` output."""
        return self._run(["version", "-json"], cwd=None)

    # ── private helpers ───────────────────────────────────────────────────────

    def _validated_path(self, path: str) -> Path:
        """
        Resolve *path* fully (following symlinks) and verify it sits inside
        the allowed base directory.

        Using ``Path.resolve()`` with no arguments dereferences all symlinks,
        which prevents symlink-escape attacks where a link inside the allowed
        base points to a directory outside it.

        Raises:
            TerraformPathError: if the path escapes the allowed base or does
                                not exist as a directory.
        """
        try:
            resolved = Path(path).resolve(strict=True)
        except FileNotFoundError:
            raise TerraformPathError(
                f"Path '{path}' does not exist."
            )

        try:
            resolved.relative_to(self._allowed_base)
        except ValueError:
            raise TerraformPathError(
                f"Path '{resolved}' is outside the allowed Terraform base "
                f"directory '{self._allowed_base}'. "
                "Set TERRAFORM_ALLOWED_BASE_DIR to change the allowed root."
            )

        if not resolved.is_dir():
            raise TerraformPathError(
                f"Path '{resolved}' exists but is not a directory."
            )
        return resolved

    def _ensure_initialized(self, work_dir: Path) -> None:
        """Run ``terraform init`` if the .terraform directory is missing.

        Called inside the per-path lock so concurrent callers will not
        double-init the same directory.
        """
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
        Timeout is read from TERRAFORM_TIMEOUT_SECONDS (default 600 s).
        """
        cmd = [self._binary] + args
        log.debug("terraform_exec", cmd=cmd, cwd=str(cwd) if cwd else None)

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except FileNotFoundError:
            raise TerraformRunError(
                f"Terraform binary '{self._binary}' not found. "
                "Install Terraform and ensure it is on PATH."
            )
        except subprocess.TimeoutExpired:
            raise TerraformRunError(
                f"Terraform command timed out after {self._timeout} seconds. "
                "Increase TERRAFORM_TIMEOUT_SECONDS if your plan/apply takes longer."
            )

        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
        }
