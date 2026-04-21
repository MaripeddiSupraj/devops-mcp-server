"""tools/helm/helm_tools.py — Helm release management tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.helm_runner import HelmRunner

# ── helm_list ────────────────────────────────────────────────────────────────

LIST_TOOL_NAME = "helm_list"
LIST_TOOL_DESCRIPTION = (
    "Lists Helm releases in a namespace (or all namespaces). "
    "Shows name, chart, version, status, and last deployed timestamp."
)
LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "namespace": {"type": "string", "description": "Kubernetes namespace (omit for default namespace)."},
        "all_namespaces": {
            "type": "boolean",
            "description": "List releases across all namespaces.",
            "default": False,
        },
    },
    "additionalProperties": False,
}


def list_handler(namespace: Optional[str] = None, all_namespaces: bool = False) -> List[Dict[str, Any]]:
    return HelmRunner().list_releases(namespace=namespace, all_namespaces=all_namespaces)


# ── helm_install ─────────────────────────────────────────────────────────────

INSTALL_TOOL_NAME = "helm_install"
INSTALL_TOOL_DESCRIPTION = (
    "Installs a Helm chart as a new release. Waits for all resources to be ready. "
    "Use helm_upgrade with install=true for idempotent installs."
)
INSTALL_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "release_name": {"type": "string", "description": "Name for the Helm release."},
        "chart": {"type": "string", "description": "Chart reference (e.g. 'bitnami/nginx', './my-chart', or OCI ref)."},
        "namespace": {"type": "string", "description": "Target Kubernetes namespace (default: 'default').", "default": "default"},
        "version": {"type": "string", "description": "Chart version to install (optional, defaults to latest)."},
        "values": {"type": "object", "description": "Values to override (merged with chart defaults)."},
        "create_namespace": {"type": "boolean", "description": "Create the namespace if it does not exist.", "default": False},
    },
    "required": ["release_name", "chart"],
    "additionalProperties": False,
}


def install_handler(
    release_name: str,
    chart: str,
    namespace: str = "default",
    version: Optional[str] = None,
    values: Optional[Dict[str, Any]] = None,
    create_namespace: bool = False,
) -> Dict[str, Any]:
    return HelmRunner().install(release_name, chart, namespace, values, version, create_namespace)


# ── helm_upgrade ─────────────────────────────────────────────────────────────

UPGRADE_TOOL_NAME = "helm_upgrade"
UPGRADE_TOOL_DESCRIPTION = (
    "Upgrades an existing Helm release to a new chart version or values. "
    "With install=true behaves as an upsert (install if not present)."
)
UPGRADE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "release_name": {"type": "string", "description": "Existing Helm release name."},
        "chart": {"type": "string", "description": "Chart reference."},
        "namespace": {"type": "string", "description": "Kubernetes namespace.", "default": "default"},
        "version": {"type": "string", "description": "Target chart version (optional)."},
        "values": {"type": "object", "description": "Values to override."},
        "install": {"type": "boolean", "description": "Install if not already deployed (upsert).", "default": True},
    },
    "required": ["release_name", "chart"],
    "additionalProperties": False,
}


def upgrade_handler(
    release_name: str,
    chart: str,
    namespace: str = "default",
    version: Optional[str] = None,
    values: Optional[Dict[str, Any]] = None,
    install: bool = True,
) -> Dict[str, Any]:
    return HelmRunner().upgrade(release_name, chart, namespace, values, version, install)


# ── helm_rollback ─────────────────────────────────────────────────────────────

ROLLBACK_TOOL_NAME = "helm_rollback"
ROLLBACK_TOOL_DESCRIPTION = (
    "Rolls back a Helm release to a previous revision. "
    "Omit revision to roll back to the immediately previous version."
)
ROLLBACK_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "release_name": {"type": "string", "description": "Helm release name to roll back."},
        "namespace": {"type": "string", "description": "Kubernetes namespace.", "default": "default"},
        "revision": {"type": "integer", "description": "Target revision number (omit for previous revision)."},
    },
    "required": ["release_name"],
    "additionalProperties": False,
}


def rollback_handler(release_name: str, namespace: str = "default", revision: Optional[int] = None) -> Dict[str, Any]:
    return HelmRunner().rollback(release_name, namespace, revision)


# ── helm_status ───────────────────────────────────────────────────────────────

STATUS_TOOL_NAME = "helm_status"
STATUS_TOOL_DESCRIPTION = (
    "Returns the status of a deployed Helm release including chart version, "
    "app version, last deployed time, and resource state."
)
STATUS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "release_name": {"type": "string", "description": "Helm release name."},
        "namespace": {"type": "string", "description": "Kubernetes namespace.", "default": "default"},
    },
    "required": ["release_name"],
    "additionalProperties": False,
}


def status_handler(release_name: str, namespace: str = "default") -> Dict[str, Any]:
    return HelmRunner().status(release_name, namespace)
