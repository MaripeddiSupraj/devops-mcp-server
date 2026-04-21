"""
integrations/helm_runner.py
---------------------------
Subprocess wrapper around the Helm CLI.

Security design mirrors terraform_runner:
- Binary path validated against settings.
- No shell=True; args passed as list.
- Output fully captured; raw process never exposed.
- Kubeconfig path injected via env var, not shell expansion.
"""

from __future__ import annotations

import json as _json
import os
import subprocess
from typing import Any, Dict, List, Optional

from core.config import get_settings
from core.logger import get_logger

log = get_logger(__name__)


class HelmRunError(RuntimeError):
    """Raised when the Helm CLI exits non-zero."""


class HelmRunner:
    """Executes Helm CLI commands and returns structured output."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._binary = getattr(self._settings, "helm_binary", "helm")
        self._timeout = getattr(self._settings, "helm_timeout_seconds", 300)
        kubeconfig = getattr(self._settings, "kubeconfig_path", None)
        self._env = {**os.environ}
        if kubeconfig:
            self._env["KUBECONFIG"] = kubeconfig

    # ── public interface ─────────────────────────────────────────────────────

    def list_releases(self, namespace: Optional[str] = None, all_namespaces: bool = False) -> List[Dict[str, Any]]:
        args = ["list", "--output", "json"]
        if all_namespaces:
            args.append("--all-namespaces")
        elif namespace:
            args += ["--namespace", namespace]
        result = self._run(args)
        releases = _json.loads(result["stdout"]) if result["stdout"].strip() else []
        return releases

    def install(
        self,
        release_name: str,
        chart: str,
        namespace: str = "default",
        values: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
        create_namespace: bool = False,
    ) -> dict:
        args = ["install", release_name, chart, "--namespace", namespace, "--output", "json", "--wait"]
        if version:
            args += ["--version", version]
        if create_namespace:
            args.append("--create-namespace")
        if values:
            import tempfile, yaml as _yaml  # noqa: E401
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                _yaml.dump(values, f)
                args += ["--values", f.name]
        return self._run(args)

    def upgrade(
        self,
        release_name: str,
        chart: str,
        namespace: str = "default",
        values: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
        install: bool = True,
    ) -> dict:
        args = ["upgrade", release_name, chart, "--namespace", namespace, "--output", "json", "--wait"]
        if install:
            args.append("--install")
        if version:
            args += ["--version", version]
        if values:
            import tempfile, yaml as _yaml  # noqa: E401
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                _yaml.dump(values, f)
                args += ["--values", f.name]
        return self._run(args)

    def rollback(self, release_name: str, namespace: str = "default", revision: Optional[int] = None) -> dict:
        args = ["rollback", release_name, "--namespace", namespace, "--wait"]
        if revision is not None:
            args.append(str(revision))
        return self._run(args)

    def status(self, release_name: str, namespace: str = "default") -> dict:
        args = ["status", release_name, "--namespace", namespace, "--output", "json"]
        result = self._run(args)
        if result["exit_code"] == 0 and result["stdout"].strip():
            try:
                result["release"] = _json.loads(result["stdout"])
            except ValueError:
                pass
        return result

    # ── private helpers ───────────────────────────────────────────────────────

    def _run(self, args: List[str]) -> dict:
        cmd = [self._binary] + args
        log.debug("helm_exec", cmd=cmd)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                env=self._env,
            )
        except FileNotFoundError:
            raise HelmRunError(
                f"Helm binary '{self._binary}' not found. Install Helm and ensure it is on PATH."
            )
        except subprocess.TimeoutExpired:
            raise HelmRunError(f"Helm command timed out after {self._timeout} seconds.")
        return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}
