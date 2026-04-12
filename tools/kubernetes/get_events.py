"""
tools/kubernetes/get_events.py
-------------------------------
MCP tool definition for ``k8s_get_events``.

Events are the Kubernetes equivalent of an audit/diagnostic log —
they reveal OOMKills, image pull failures, scheduling issues, probe
failures, and more. Always check these when pods are misbehaving.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.k8s_client import KubernetesClient

TOOL_NAME = "k8s_get_events"
TOOL_DESCRIPTION = (
    "Lists Kubernetes events in a namespace, sorted with Warning events first. "
    "Invaluable for diagnosing OOMKills, ImagePullBackOff, CrashLoopBackOff, "
    "scheduling failures, and probe failures. "
    "Optionally filter to a specific pod or object with field_selector."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "namespace": {
            "type": "string",
            "description": "Kubernetes namespace to query.",
            "default": "default",
        },
        "field_selector": {
            "type": "string",
            "description": (
                "Optional Kubernetes field selector to narrow results. "
                "Examples: 'involvedObject.name=my-pod', 'type=Warning'."
            ),
        },
    },
    "additionalProperties": False,
}


def handler(
    namespace: str = "default",
    field_selector: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch namespace events, warnings first.

    Returns:
        List of event dicts with ``type``, ``reason``, ``message``, ``object``,
        ``count``, ``first_time``, ``last_time``.
    """
    return KubernetesClient().get_events(
        namespace=namespace,
        field_selector=field_selector,
    )
