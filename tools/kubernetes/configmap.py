"""tools/kubernetes/configmap.py — Kubernetes ConfigMap tools."""

from __future__ import annotations

from typing import Any, Dict

from integrations.k8s_client import KubernetesClient

GET_TOOL_NAME = "k8s_get_configmap"
GET_TOOL_DESCRIPTION = "Fetches a Kubernetes ConfigMap by name. Returns all key names and values."
GET_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "ConfigMap name."},
        "namespace": {"type": "string", "description": "Kubernetes namespace.", "default": "default"},
    },
    "required": ["name"],
    "additionalProperties": False,
}

APPLY_TOOL_NAME = "k8s_apply_configmap"
APPLY_TOOL_DESCRIPTION = (
    "Creates or updates a Kubernetes ConfigMap with the provided key/value data. "
    "Idempotent — safe to run multiple times."
)
APPLY_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "ConfigMap name."},
        "data": {"type": "object", "description": "Key/value pairs to store in the ConfigMap."},
        "namespace": {"type": "string", "description": "Kubernetes namespace.", "default": "default"},
    },
    "required": ["name", "data"],
    "additionalProperties": False,
}


def get_handler(name: str, namespace: str = "default") -> Dict[str, Any]:
    return KubernetesClient().get_configmap(name, namespace)


def apply_handler(name: str, data: Dict[str, str], namespace: str = "default") -> Dict[str, Any]:
    return KubernetesClient().apply_configmap(name, data, namespace)
