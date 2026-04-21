"""tools/vault/vault_tools.py — HashiCorp Vault KV v2 secret management tools."""

from __future__ import annotations

from typing import Any, Dict, List

from integrations.vault_client import VaultClient

# ── vault_read_secret ─────────────────────────────────────────────────────────

READ_TOOL_NAME = "vault_read_secret"
READ_TOOL_DESCRIPTION = (
    "Reads a secret from HashiCorp Vault KV v2. "
    "Returns all key/value pairs at the given path along with version metadata. "
    "Requires VAULT_ADDR and VAULT_TOKEN."
)
READ_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Secret path within the KV mount (e.g. 'myapp/database')."},
    },
    "required": ["path"],
    "additionalProperties": False,
}


def read_handler(path: str) -> Dict[str, Any]:
    return VaultClient().read_secret(path)


# ── vault_write_secret ────────────────────────────────────────────────────────

WRITE_TOOL_NAME = "vault_write_secret"
WRITE_TOOL_DESCRIPTION = (
    "Writes key/value data to a Vault KV v2 path. "
    "Creates a new version if the path already exists (existing versions are preserved). "
    "Returns the new version number."
)
WRITE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Secret path within the KV mount."},
        "data": {"type": "object", "description": "Key/value pairs to store."},
    },
    "required": ["path", "data"],
    "additionalProperties": False,
}


def write_handler(path: str, data: Dict[str, str]) -> Dict[str, Any]:
    return VaultClient().write_secret(path, data)


# ── vault_list_secrets ────────────────────────────────────────────────────────

LIST_TOOL_NAME = "vault_list_secrets"
LIST_TOOL_DESCRIPTION = (
    "Lists secret paths under a given prefix in Vault KV v2. "
    "Returns key names (not values). Paths ending in '/' are sub-directories."
)
LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Prefix path to list (e.g. 'myapp/' or '')."},
    },
    "required": ["path"],
    "additionalProperties": False,
}


def list_handler(path: str) -> List[str]:
    return VaultClient().list_secrets(path)
