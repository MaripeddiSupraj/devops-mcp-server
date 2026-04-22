"""tools/security/scanner_tools.py — Trivy and tfsec security scanning tools."""

from __future__ import annotations

from typing import Any, Dict, Optional

from integrations.scanner_runner import TfsecRunner, TrivyRunner

# ── trivy_scan_image ──────────────────────────────────────────────────────────

TRIVY_IMAGE_TOOL_NAME = "trivy_scan_image"
TRIVY_IMAGE_TOOL_DESCRIPTION = (
    "Scan a Docker image for OS and library vulnerabilities using Trivy. "
    "Returns CVEs grouped by target with severity, fix version, and package name. "
    "Requires trivy to be installed (trivy binary on PATH)."
)
TRIVY_IMAGE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "image": {"type": "string", "description": "Image name:tag to scan (e.g. 'nginx:latest')."},
        "severity": {
            "type": "string",
            "description": "Comma-separated minimum severities to report (e.g. 'HIGH,CRITICAL'). Omit for all.",
        },
    },
    "required": ["image"],
    "additionalProperties": False,
}


def trivy_image_handler(image: str, severity: Optional[str] = None) -> Dict:
    return TrivyRunner().scan_image(image, severity=severity)


# ── trivy_scan_filesystem ─────────────────────────────────────────────────────

TRIVY_FS_TOOL_NAME = "trivy_scan_filesystem"
TRIVY_FS_TOOL_DESCRIPTION = (
    "Scan a local filesystem path (repo, directory) for vulnerabilities in "
    "dependency manifests (requirements.txt, package.json, go.sum, etc.) using Trivy."
)
TRIVY_FS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Absolute path to directory or file to scan."},
        "severity": {
            "type": "string",
            "description": "Comma-separated severity filter (e.g. 'HIGH,CRITICAL'). Omit for all.",
        },
    },
    "required": ["path"],
    "additionalProperties": False,
}


def trivy_fs_handler(path: str, severity: Optional[str] = None) -> Dict:
    return TrivyRunner().scan_filesystem(path, severity=severity)


# ── tfsec_scan ────────────────────────────────────────────────────────────────

TFSEC_TOOL_NAME = "tfsec_scan"
TFSEC_TOOL_DESCRIPTION = (
    "Scan a Terraform directory for security misconfigurations using tfsec. "
    "Detects issues like open security groups, unencrypted storage, missing logging, etc. "
    "Requires tfsec to be installed (tfsec binary on PATH)."
)
TFSEC_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Path to Terraform directory to scan."},
        "severity": {
            "type": "string",
            "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            "description": "Minimum severity to report (default: LOW — report all).",
        },
    },
    "required": ["path"],
    "additionalProperties": False,
}


def tfsec_handler(path: str, severity: Optional[str] = None) -> Dict:
    return TfsecRunner().scan(path, severity=severity)
