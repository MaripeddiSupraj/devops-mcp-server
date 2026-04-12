"""
tools/kubernetes/get_services.py
----------------------------------
MCP tool definition for ``k8s_get_services``.

Services are the network fabric of a cluster — you need them to know
what's exposed, on which port, and whether a LoadBalancer has an
external IP assigned yet.
"""

from __future__ import annotations

from typing import Any, Dict, List

from integrations.k8s_client import KubernetesClient

TOOL_NAME = "k8s_get_services"
TOOL_DESCRIPTION = (
    "Lists all Services in a Kubernetes namespace. "
    "Returns service type (ClusterIP/NodePort/LoadBalancer), ports, "
    "selector labels, ClusterIP, and external IP (if assigned)."
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
    List services in *namespace*.

    Returns:
        List of dicts with ``name``, ``type``, ``cluster_ip``, ``external_ip``,
        ``ports``, ``selector``.
    """
    return KubernetesClient().get_services(namespace=namespace)
