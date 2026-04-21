"""tools/kubernetes/secret.py — Kubernetes Secret listing (keys only, not values)."""

from __future__ import annotations

from typing import Any, Dict, List

from integrations.k8s_client import KubernetesClient

TOOL_NAME = "k8s_list_secrets"
TOOL_DESCRIPTION = (
    "Lists Kubernetes secrets in a namespace. "
    "Returns secret names, types, and key names ONLY — values are never exposed."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "namespace": {"type": "string", "description": "Kubernetes namespace.", "default": "default"},
    },
    "additionalProperties": False,
}


def handler(namespace: str = "default") -> List[Dict[str, Any]]:
    return KubernetesClient().list_secrets(namespace)
