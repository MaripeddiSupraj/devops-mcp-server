"""
tools/kubernetes/scale.py
--------------------------
MCP tool definition for ``k8s_scale``.

Scaling is one of the most frequent runtime operations — handling traffic
spikes, cost optimisation (scale-to-zero at night), and canary preparation.
"""

from __future__ import annotations

from typing import Any, Dict

from integrations.k8s_client import KubernetesClient

TOOL_NAME = "k8s_scale"
TOOL_DESCRIPTION = (
    "Scales a Kubernetes Deployment to the specified number of replicas. "
    "Supports scale-to-zero (replicas=0) for cost saving. "
    "Returns previous and new replica counts."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Name of the Deployment to scale.",
        },
        "replicas": {
            "type": "integer",
            "description": "Desired number of replicas (0 to scale to zero).",
            "minimum": 0,
            "maximum": 100,
        },
        "namespace": {
            "type": "string",
            "description": "Kubernetes namespace.",
            "default": "default",
        },
    },
    "required": ["name", "replicas"],
    "additionalProperties": False,
}


def handler(name: str, replicas: int, namespace: str = "default") -> Dict[str, Any]:
    """
    Scale a Deployment.

    Returns:
        Dict with ``name``, ``namespace``, ``previous_replicas``, ``new_replicas``.
    """
    return KubernetesClient().scale_deployment(
        name=name,
        replicas=replicas,
        namespace=namespace,
    )
