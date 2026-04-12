"""
tools/kubernetes/deploy.py
--------------------------
MCP tool definition for ``k8s_deploy``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from integrations.k8s_client import KubernetesClient

TOOL_NAME = "k8s_deploy"
TOOL_DESCRIPTION = (
    "Creates or updates a Kubernetes Deployment with the specified container image. "
    "If a deployment with the same name exists it is patched (rolling update)."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Deployment name.",
        },
        "image": {
            "type": "string",
            "description": "Container image including tag (e.g. nginx:1.25).",
        },
        "namespace": {
            "type": "string",
            "description": "Kubernetes namespace.",
            "default": "default",
        },
        "replicas": {
            "type": "integer",
            "description": "Number of pod replicas.",
            "minimum": 1,
            "maximum": 50,
            "default": 1,
        },
        "port": {
            "type": "integer",
            "description": "Container port to expose.",
            "default": 80,
        },
    },
    "required": ["name", "image"],
    "additionalProperties": False,
}


def handler(
    name: str,
    image: str,
    namespace: str = "default",
    replicas: int = 1,
    port: int = 80,
) -> Dict[str, Any]:
    """
    Deploy or update a Kubernetes workload.

    Returns:
        Dict with deployment ``name``, ``namespace``, ``replicas``, ``image``, ``action``.
    """
    k8s = KubernetesClient()
    return k8s.deploy(
        name=name,
        image=image,
        namespace=namespace,
        replicas=replicas,
        port=port,
    )
