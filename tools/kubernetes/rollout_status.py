"""
tools/kubernetes/rollout_status.py
-----------------------------------
MCP tool definition for ``k8s_rollout_status``.

After deploying or restarting, an AI agent must be able to verify
whether the rollout completed successfully before declaring success.
This tool provides that signal.
"""

from __future__ import annotations

from typing import Any, Dict

from integrations.k8s_client import KubernetesClient

TOOL_NAME = "k8s_rollout_status"
TOOL_DESCRIPTION = (
    "Returns the current rollout status of a Kubernetes Deployment. "
    "Reports desired vs updated/ready/available replica counts and a "
    "boolean `complete` flag. "
    "Use this to verify a deploy or rollout_restart succeeded."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Name of the Deployment to check.",
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
    Check rollout progress.

    Returns:
        Dict with ``desired``, ``updated``, ``ready``, ``available``, ``complete``.
    """
    return KubernetesClient().rollout_status(name=name, namespace=namespace)
