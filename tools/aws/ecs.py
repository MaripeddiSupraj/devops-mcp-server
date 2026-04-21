"""tools/aws/ecs.py — AWS ECS cluster, service, and task tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.aws_client import ECSClient

# ── aws_ecs_list_clusters ─────────────────────────────────────────────────────

LIST_CLUSTERS_TOOL_NAME = "aws_ecs_list_clusters"
LIST_CLUSTERS_TOOL_DESCRIPTION = (
    "Lists all ECS clusters in the current region. "
    "Shows name, status, running/pending task counts, and active service count."
)
LIST_CLUSTERS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def list_clusters_handler() -> List[Dict[str, Any]]:
    return ECSClient().list_clusters()


# ── aws_ecs_list_services ─────────────────────────────────────────────────────

LIST_SERVICES_TOOL_NAME = "aws_ecs_list_services"
LIST_SERVICES_TOOL_DESCRIPTION = (
    "Lists ECS services in a cluster. Shows name, status, desired/running/pending counts, "
    "task definition, and launch type (EC2 or Fargate)."
)
LIST_SERVICES_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "cluster": {"type": "string", "description": "ECS cluster name or ARN."},
    },
    "required": ["cluster"],
    "additionalProperties": False,
}


def list_services_handler(cluster: str) -> List[Dict[str, Any]]:
    return ECSClient().list_services(cluster)


# ── aws_ecs_list_tasks ────────────────────────────────────────────────────────

LIST_TASKS_TOOL_NAME = "aws_ecs_list_tasks"
LIST_TASKS_TOOL_DESCRIPTION = (
    "Lists running tasks in an ECS cluster, optionally filtered by service. "
    "Shows task ID, status, task definition, launch type, and start time."
)
LIST_TASKS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "cluster": {"type": "string", "description": "ECS cluster name or ARN."},
        "service": {"type": "string", "description": "Filter by service name (optional)."},
    },
    "required": ["cluster"],
    "additionalProperties": False,
}


def list_tasks_handler(cluster: str, service: Optional[str] = None) -> List[Dict[str, Any]]:
    return ECSClient().list_tasks(cluster, service)


# ── aws_ecs_deploy_service ────────────────────────────────────────────────────

DEPLOY_TOOL_NAME = "aws_ecs_deploy_service"
DEPLOY_TOOL_DESCRIPTION = (
    "Updates an ECS service — triggers a new deployment with force_new_deployment=true, "
    "or scales to a new desired count. Use to roll out a new task definition revision."
)
DEPLOY_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "cluster": {"type": "string", "description": "ECS cluster name or ARN."},
        "service": {"type": "string", "description": "ECS service name."},
        "desired_count": {"type": "integer", "description": "New desired task count (optional — omit to keep current)."},
        "force_new_deployment": {
            "type": "boolean",
            "description": "Force a new deployment with the current task definition (useful to pull latest image).",
            "default": True,
        },
    },
    "required": ["cluster", "service"],
    "additionalProperties": False,
}


def deploy_handler(cluster: str, service: str, desired_count: Optional[int] = None, force_new_deployment: bool = True) -> Dict[str, Any]:
    return ECSClient().update_service(cluster, service, desired_count, force_new_deployment)
