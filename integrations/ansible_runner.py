"""integrations/ansible_runner.py — Ansible CLI subprocess wrapper."""

from __future__ import annotations

import json
import subprocess
from typing import Any, Dict, List, Optional

from core.config import get_settings


class AnsibleRunner:
    def __init__(self) -> None:
        cfg = get_settings()
        self._bin = cfg.ansible_binary
        self._playbook_bin = cfg.ansible_playbook_binary
        self._timeout = cfg.ansible_timeout_seconds

    def _run(self, cmd: List[str]) -> str:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=self._timeout)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result.stdout.strip()

    def run_playbook(
        self,
        playbook: str,
        inventory: Optional[str] = None,
        extra_vars: Optional[Dict[str, str]] = None,
        limit: Optional[str] = None,
        tags: Optional[str] = None,
        check: bool = False,
    ) -> str:
        cmd = [self._playbook_bin, playbook]
        if inventory:
            cmd += ["-i", inventory]
        if extra_vars:
            for k, v in extra_vars.items():
                cmd += ["-e", f"{k}={v}"]
        if limit:
            cmd += ["--limit", limit]
        if tags:
            cmd += ["--tags", tags]
        if check:
            cmd.append("--check")
        return self._run(cmd)

    def list_hosts(self, inventory: str, pattern: str = "all") -> List[str]:
        cmd = [self._bin, "-i", inventory, pattern, "--list-hosts"]
        output = self._run(cmd)
        hosts = []
        for line in output.splitlines():
            line = line.strip()
            if line and not line.startswith("hosts ("):
                hosts.append(line)
        return hosts

    def ping(self, inventory: str, pattern: str = "all") -> str:
        cmd = [self._bin, "-i", inventory, pattern, "-m", "ping"]
        return self._run(cmd)

    def run_module(self, inventory: str, pattern: str, module: str, args: Optional[str] = None) -> str:
        cmd = [self._bin, "-i", inventory, pattern, "-m", module]
        if args:
            cmd += ["-a", args]
        return self._run(cmd)
