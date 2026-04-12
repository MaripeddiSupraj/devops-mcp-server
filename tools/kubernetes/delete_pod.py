"""
tools/kubernetes/delete_pod.py
--------------------------------
MCP tool definition for ``k8s_delete_pod``.

Deleting a pod (when it belongs to a Deployment/ReplicaSet) is a
safe, targeted restart — Kubernetes immediately recreates it. This
is the surgical alternative to a full rollout_restart when only one
pod is stuck or has stale state.
"""

from __future__ import annotations

from typing import Any, Dict

from integrations.k8s_client import KubernetesClient

TOOL_NAME = "k8s_delete_pod"
TOOL_DESCRIPTION = (
    "Deletes a specific Kubernetes pod. "
    "If the pod is managed by a Deployment or ReplicaSet, Kubernetes will "
    "automatically recreate it (safe targeted restart). "
    "Set grace_period_seconds=0 for immediate termination."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "pod_name": {
            "type": "string",
            "description": "Exact name of the pod to delete.",
        },
        "namespace": {
            "type": "string",
            "description": "Kubernetes namespace.",
            "default": "default",
        },
        "grace_period_seconds": {
            "type": "integer",
            "description": "Termination grace period. 0 = immediate kill. Default 30.",
            "minimum": 0,
            "maximum": 300,
            "default": 30,
        },
    },
    "required": ["pod_name"],
    "additionalProperties": False,
}


def handler(
    pod_name: str,
    namespace: str = "default",
    grace_period_seconds: int = 30,
) -> Dict[str, Any]:
    """
    Delete a pod and confirm the action.

    Returns:
        Dict with ``pod``, ``namespace``, ``action``, ``grace_period_seconds``, ``message``.
    """
    return KubernetesClient().delete_pod(
        pod_name=pod_name,
        namespace=namespace,
        grace_period_seconds=grace_period_seconds,
    )
