"""
tools/kubernetes/get_logs.py
-----------------------------
MCP tool definition for ``k8s_get_logs``.
The single most-used debugging command in any Kubernetes workflow.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from integrations.k8s_client import KubernetesClient

TOOL_NAME = "k8s_get_logs"
TOOL_DESCRIPTION = (
    "Fetches logs from a Kubernetes pod container. "
    "Returns the last N lines of stdout/stderr. "
    "Set previous=true to retrieve logs from a crashed (previous) container instance."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "pod_name": {
            "type": "string",
            "description": "Name of the pod to retrieve logs from.",
        },
        "namespace": {
            "type": "string",
            "description": "Kubernetes namespace.",
            "default": "default",
        },
        "container": {
            "type": "string",
            "description": "Container name (optional — auto-selected for single-container pods).",
        },
        "tail_lines": {
            "type": "integer",
            "description": "Number of lines to return from the end of the log.",
            "default": 100,
            "minimum": 1,
            "maximum": 5000,
        },
        "previous": {
            "type": "boolean",
            "description": "Return logs from the previous (crashed) container instance.",
            "default": False,
        },
    },
    "required": ["pod_name"],
    "additionalProperties": False,
}


def handler(
    pod_name: str,
    namespace: str = "default",
    container: Optional[str] = None,
    tail_lines: int = 100,
    previous: bool = False,
) -> Dict[str, Any]:
    """
    Retrieve pod logs.

    Returns:
        Dict with ``pod``, ``container``, ``lines``, ``log`` (full text).
    """
    return KubernetesClient().get_logs(
        pod_name=pod_name,
        namespace=namespace,
        container=container,
        tail_lines=tail_lines,
        previous=previous,
    )
