"""
tools/kubernetes/get_deployments.py
-------------------------------------
MCP tool definition for ``k8s_get_deployments``.

Listing deployments is the first thing any operator does when walking
into a namespace — it gives a fleet-level view of what is running,
its image, and health.
"""

from __future__ import annotations

from typing import Any, Dict, List

from integrations.k8s_client import KubernetesClient

TOOL_NAME = "k8s_get_deployments"
TOOL_DESCRIPTION = (
    "Lists all Deployments in a Kubernetes namespace with their replica counts, "
    "current container image, and readiness conditions."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "namespace": {
            "type": "string",
            "description": "Kubernetes namespace.",
            "default": "default",
        }
    },
    "additionalProperties": False,
}


def handler(namespace: str = "default") -> List[Dict[str, Any]]:
    """
    List Deployments in *namespace*.

    Returns:
        List of dicts with ``name``, ``replicas``, ``available``, ``ready``, ``image``.
    """
    return KubernetesClient().get_deployments(namespace=namespace)
