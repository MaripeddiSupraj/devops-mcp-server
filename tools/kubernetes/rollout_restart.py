"""
tools/kubernetes/rollout_restart.py
-------------------------------------
MCP tool definition for ``k8s_rollout_restart``.

Rolling restart is the standard way to force pods to re-read a ConfigMap,
pick up new environment variables, or clear in-memory state — without
any downtime (assuming replicas > 1).
"""

from __future__ import annotations

from typing import Any, Dict

from integrations.k8s_client import KubernetesClient

TOOL_NAME = "k8s_rollout_restart"
TOOL_DESCRIPTION = (
    "Triggers a rolling restart of a Kubernetes Deployment with zero downtime. "
    "Equivalent to `kubectl rollout restart deployment/<name>`. "
    "Use this to force pods to reload ConfigMaps, secrets, or clear in-memory state."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Name of the Deployment to restart.",
        },
        "namespace": {
            "type": "string",
            "description": "Kubernetes namespace.",
            "default": "default",
        },
    },
    "required": ["name"],
    "additionalProperties": False,
}


def handler(name: str, namespace: str = "default") -> Dict[str, Any]:
    """
    Trigger a rolling restart.

    Returns:
        Dict with ``name``, ``namespace``, ``action``, ``triggered_at``, ``message``.
    """
    return KubernetesClient().rollout_restart(name=name, namespace=namespace)
