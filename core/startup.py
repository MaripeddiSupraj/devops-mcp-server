"""
core/startup.py
---------------
Startup credential and configuration validation.

Runs once at server boot and collects non-fatal warnings so operators
can see misconfiguration immediately via GET /health rather than waiting
for a tool call to fail at runtime.

Design:
- Every check returns a warning string or None.
- All checks run unconditionally — we want a full picture, not fail-fast.
- Nothing here raises; a missing credential is a warning, not a crash.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional

from core.config import Settings
from core.logger import get_logger

log = get_logger(__name__)


def _check_github(settings: Settings) -> Optional[str]:
    if not settings.github_token:
        return (
            "GITHUB_TOKEN is not set — github_create_pull_request and "
            "github_get_repo will fail at runtime."
        )
    return None


def _check_aws(settings: Settings) -> Optional[str]:
    has_key = bool(settings.aws_access_key_id)
    has_secret = bool(settings.aws_secret_access_key)
    if not has_key and not has_secret:
        return (
            "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are not set — "
            "AWS tools will fail unless an IAM role or SSO session is active."
        )
    if has_key != has_secret:
        return (
            "Only one of AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY is set — "
            "both must be provided together."
        )
    return None


def _check_kubeconfig(settings: Settings) -> Optional[str]:
    kubeconfig = settings.kubeconfig_path
    if not kubeconfig:
        # In-cluster config may still work; warn but don't hard-fail.
        return (
            "KUBECONFIG is not set — Kubernetes tools will attempt in-cluster "
            "config. Set KUBECONFIG explicitly if running outside a cluster."
        )
    path = Path(kubeconfig)
    if not path.exists():
        return (
            f"KUBECONFIG path '{kubeconfig}' does not exist — "
            "Kubernetes tools will fail at runtime."
        )
    return None


def _check_terraform(settings: Settings) -> Optional[str]:
    binary = settings.terraform_binary
    if not shutil.which(binary):
        return (
            f"Terraform binary '{binary}' not found on PATH — "
            "terraform_plan / apply / destroy will fail. "
            "Install Terraform or set TERRAFORM_BINARY to the correct path."
        )
    return None


def collect_startup_warnings(settings: Settings) -> List[str]:
    """
    Run all credential/config checks and return a list of warning strings.

    Called once at startup; result is cached in the module and served via
    GET /health so operators see issues immediately without making a tool call.
    """
    checkers = [
        _check_github,
        _check_aws,
        _check_kubeconfig,
        _check_terraform,
    ]

    warnings: List[str] = []
    for checker in checkers:
        warning = checker(settings)
        if warning:
            warnings.append(warning)
            log.warning("startup_warning", message=warning)

    if not warnings:
        log.info("startup_checks_passed", message="All credential checks passed.")

    return warnings
