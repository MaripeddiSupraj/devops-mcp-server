"""tools/argocd/argocd_tools.py — ArgoCD GitOps application management tools."""

from __future__ import annotations

from typing import Any, Dict, List

from integrations.argocd_client import ArgoCDClient

# ── argocd_list_apps ──────────────────────────────────────────────────────────

LIST_TOOL_NAME = "argocd_list_apps"
LIST_TOOL_DESCRIPTION = (
    "Lists all ArgoCD applications. Shows name, project, source repo/path, "
    "target namespace, sync status, and health status. "
    "Requires ARGOCD_SERVER_URL and ARGOCD_AUTH_TOKEN."
)
LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def list_handler() -> List[Dict[str, Any]]:
    return ArgoCDClient().list_apps()


# ── argocd_app_status ─────────────────────────────────────────────────────────

STATUS_TOOL_NAME = "argocd_app_status"
STATUS_TOOL_DESCRIPTION = (
    "Returns detailed status for a specific ArgoCD application. "
    "Shows sync status, health status, current revision, conditions, "
    "and per-resource health."
)
STATUS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "ArgoCD application name."},
    },
    "required": ["name"],
    "additionalProperties": False,
}


def status_handler(name: str) -> Dict[str, Any]:
    return ArgoCDClient().get_app(name)


# ── argocd_sync_app ───────────────────────────────────────────────────────────

SYNC_TOOL_NAME = "argocd_sync_app"
SYNC_TOOL_DESCRIPTION = (
    "Triggers a sync for an ArgoCD application — applies the desired Git state to the cluster. "
    "Set prune=true to delete resources removed from Git. "
    "Set dry_run=true to preview changes without applying."
)
SYNC_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "ArgoCD application name."},
        "prune": {"type": "boolean", "description": "Delete resources not in Git (default: false).", "default": False},
        "dry_run": {"type": "boolean", "description": "Preview without applying (default: false).", "default": False},
    },
    "required": ["name"],
    "additionalProperties": False,
}


def sync_handler(name: str, prune: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    return ArgoCDClient().sync_app(name, prune=prune, dry_run=dry_run)


# ── argocd_rollback_app ───────────────────────────────────────────────────────

ROLLBACK_TOOL_NAME = "argocd_rollback_app"
ROLLBACK_TOOL_DESCRIPTION = (
    "Rolls back an ArgoCD application to a specific history revision ID. "
    "Use argocd_app_status to find the current revision, then decrement for rollback."
)
ROLLBACK_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "ArgoCD application name."},
        "revision_id": {"type": "integer", "description": "History revision ID to roll back to."},
    },
    "required": ["name", "revision_id"],
    "additionalProperties": False,
}


def rollback_handler(name: str, revision_id: int) -> Dict[str, Any]:
    return ArgoCDClient().rollback_app(name, revision_id)
