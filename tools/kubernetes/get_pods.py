"""
tools/kubernetes/get_pods.py
-----------------------------
MCP tool definition for ``k8s_get_pods``.
"""

from __future__ import annotations

from typing import Any, Dict, List

from integrations.k8s_client import KubernetesClient

TOOL_NAME = "k8s_get_pods"
TOOL_DESCRIPTION = (
    "Lists all pods in a Kubernetes namespace with their status, "
    "readiness, restart count, node assignment, and IP address."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "namespace": {
            "type": "string",
            "description": "Kubernetes namespace to query.",
            "default": "default",
        }
    },
    "additionalProperties": False,
}


def handler(namespace: str = "default") -> List[Dict[str, Any]]:
    """
    Return pod list for *namespace*.

    Returns:
        List of dicts with ``name``, ``status``, ``ready``, ``restarts``, ``node``, ``ip``.
    """
    k8s = KubernetesClient()
    return k8s.get_pods(namespace=namespace)
