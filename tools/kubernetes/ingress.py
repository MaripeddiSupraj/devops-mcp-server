"""tools/kubernetes/ingress.py — Kubernetes Ingress listing tool."""

from __future__ import annotations

from typing import Any, Dict, List

from integrations.k8s_client import KubernetesClient

TOOL_NAME = "k8s_list_ingresses"
TOOL_DESCRIPTION = (
    "Lists Kubernetes Ingress resources in a namespace. "
    "Shows ingress class, routing rules (host → paths), and TLS configuration."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "namespace": {"type": "string", "description": "Kubernetes namespace.", "default": "default"},
    },
    "additionalProperties": False,
}


def handler(namespace: str = "default") -> List[Dict[str, Any]]:
    return KubernetesClient().list_ingresses(namespace)
