"""tools/kubernetes/jobs.py — Kubernetes Job and CronJob tools."""

from __future__ import annotations

from typing import Any, Dict, List

from integrations.k8s_client import KubernetesClient

LIST_JOBS_TOOL_NAME = "k8s_list_jobs"
LIST_JOBS_TOOL_DESCRIPTION = (
    "Lists Kubernetes Jobs in a namespace. "
    "Shows name, active/succeeded/failed task counts, start time, and completion time."
)
LIST_JOBS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "namespace": {"type": "string", "description": "Kubernetes namespace.", "default": "default"},
    },
    "additionalProperties": False,
}

LIST_CRONJOBS_TOOL_NAME = "k8s_list_cronjobs"
LIST_CRONJOBS_TOOL_DESCRIPTION = (
    "Lists Kubernetes CronJobs in a namespace. "
    "Shows name, cron schedule, suspended status, last schedule time, and active job count."
)
LIST_CRONJOBS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "namespace": {"type": "string", "description": "Kubernetes namespace.", "default": "default"},
    },
    "additionalProperties": False,
}


def list_jobs_handler(namespace: str = "default") -> List[Dict[str, Any]]:
    return KubernetesClient().list_jobs(namespace)


def list_cronjobs_handler(namespace: str = "default") -> List[Dict[str, Any]]:
    return KubernetesClient().list_cronjobs(namespace)
