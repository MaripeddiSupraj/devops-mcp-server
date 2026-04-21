"""tools/kubernetes/namespace.py — Kubernetes namespace tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.k8s_client import KubernetesClient

LIST_TOOL_NAME = "k8s_list_namespaces"
LIST_TOOL_DESCRIPTION = "Lists all Kubernetes namespaces in the cluster with their status and labels."
LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {"type": "object", "properties": {}, "additionalProperties": False}

CREATE_TOOL_NAME = "k8s_create_namespace"
CREATE_TOOL_DESCRIPTION = "Creates a new Kubernetes namespace with optional labels."
CREATE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Namespace name."},
        "labels": {"type": "object", "description": "Key/value labels to apply (optional)."},
    },
    "required": ["name"],
    "additionalProperties": False,
}


def list_handler() -> List[Dict[str, Any]]:
    return KubernetesClient().list_namespaces()


def create_handler(name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    return KubernetesClient().create_namespace(name, labels)
