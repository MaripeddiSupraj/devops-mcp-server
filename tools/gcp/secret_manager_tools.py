"""tools/gcp/secret_manager_tools.py — GCP Secret Manager tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.gcp_client import GCPSecretManagerClient

# ── gcp_secret_manager_list ───────────────────────────────────────────────────

LIST_SECRETS_TOOL_NAME = "gcp_secret_manager_list"
LIST_SECRETS_TOOL_DESCRIPTION = (
    "List all secrets in GCP Secret Manager for the configured project. "
    "Returns secret names only — not values. Requires GCP_PROJECT_ID."
)
LIST_SECRETS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def list_secrets_handler() -> List[Dict]:
    return GCPSecretManagerClient().list_secrets()


# ── gcp_secret_manager_get ────────────────────────────────────────────────────

GET_SECRET_TOOL_NAME = "gcp_secret_manager_get"
GET_SECRET_TOOL_DESCRIPTION = "Get a secret value from GCP Secret Manager by secret ID."
GET_SECRET_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "secret_id": {"type": "string", "description": "Secret ID (name) in Secret Manager."},
        "version": {"type": "string", "description": "Secret version (default: 'latest').", "default": "latest"},
    },
    "required": ["secret_id"],
    "additionalProperties": False,
}


def get_secret_handler(secret_id: str, version: str = "latest") -> Dict:
    return GCPSecretManagerClient().get_secret(secret_id, version=version)


# ── gcp_secret_manager_create ─────────────────────────────────────────────────

CREATE_SECRET_TOOL_NAME = "gcp_secret_manager_create"
CREATE_SECRET_TOOL_DESCRIPTION = "Create a new secret in GCP Secret Manager with an initial value."
CREATE_SECRET_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "secret_id": {"type": "string", "description": "Secret ID to create."},
        "value": {"type": "string", "description": "Initial secret value."},
    },
    "required": ["secret_id", "value"],
    "additionalProperties": False,
}


def create_secret_handler(secret_id: str, value: str) -> Dict:
    return GCPSecretManagerClient().create_secret(secret_id, value)
