"""
tools/kubernetes/get_nodes.py
------------------------------
MCP tool definition for ``k8s_get_nodes``.

Node health is the foundation of cluster reliability. An AI agent
diagnosing degraded pods should check nodes first — a NotReady node
explains many pod failures without any further investigation.
"""

from __future__ import annotations

from typing import Any, Dict, List

from integrations.k8s_client import KubernetesClient

TOOL_NAME = "k8s_get_nodes"
TOOL_DESCRIPTION = (
    "Returns health and capacity information for all nodes in the cluster. "
    "Includes Ready status, roles (control-plane/worker), Kubernetes version, "
    "OS image, container runtime, and CPU/memory capacity."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def handler() -> List[Dict[str, Any]]:
    """
    Get cluster node status.

    Returns:
        List of node dicts with ``name``, ``ready``, ``roles``, ``k8s_version``,
        ``os``, ``cpu``, ``memory``.
    """
    return KubernetesClient().get_nodes()
