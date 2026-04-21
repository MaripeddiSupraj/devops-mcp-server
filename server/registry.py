"""
server/registry.py
------------------
Tool registry — a simple in-memory store that maps tool names to
ToolEntry objects (metadata + handler callable).

New tools are registered by calling ``registry.register()``.
The registry is a singleton; all modules import the same instance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


from core.logger import get_logger
from server.schemas import ToolDefinition

log = get_logger(__name__)


@dataclass
class ToolEntry:
    """
    Combines a tool's MCP metadata with its Python handler.

    Attributes:
        name:            Unique tool identifier used in API calls.
        description:     Human/AI-readable description of what the tool does.
        input_schema:    JSON Schema object describing accepted parameters.
        handler:         Callable that executes the tool logic.
        tags:            Optional categorisation tags (e.g. ``["terraform", "iac"]``).
        timeout_seconds: Per-tool execution timeout override (0 = no timeout).
                         When None the global TOOL_TIMEOUT_SECONDS setting is used.
    """

    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Any]
    tags: List[str] = field(default_factory=list)
    timeout_seconds: Optional[int] = None

    def to_definition(self) -> ToolDefinition:
        """Return a serialisable ToolDefinition (no handler callable)."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
            tags=self.tags,
        )


class ToolRegistry:
    """
    Thread-safe, in-memory tool registry.

    Usage::

        registry = ToolRegistry()
        registry.register(ToolEntry(name="my_tool", ...))
        entry = registry.get("my_tool")
    """

    def __init__(self) -> None:
        self._tools: Dict[str, ToolEntry] = {}

    def register(self, entry: ToolEntry) -> None:
        """
        Add *entry* to the registry.

        Raises:
            ValueError: if a tool with the same name is already registered.
        """
        if entry.name in self._tools:
            raise ValueError(
                f"Tool '{entry.name}' is already registered. "
                "Use a unique name or deregister the existing entry first."
            )
        self._tools[entry.name] = entry
        log.info("tool_registered", tool=entry.name, tags=entry.tags)

    def get(self, name: str) -> Optional[ToolEntry]:
        """Return the ToolEntry for *name*, or ``None`` if not found."""
        return self._tools.get(name)

    def list_all(self) -> List[ToolEntry]:
        """Return all registered ToolEntry objects."""
        return list(self._tools.values())

    def list_names(self) -> List[str]:
        """Return sorted list of registered tool names."""
        return sorted(self._tools.keys())

    def list_definitions(self, tag: Optional[str] = None) -> List[ToolDefinition]:
        """Return ToolDefinition objects suitable for JSON serialisation.

        Args:
            tag: If provided, only return tools whose tags list contains this value.
        """
        entries = self._tools.values()
        if tag:
            entries = [e for e in entries if tag in e.tags]
        return [entry.to_definition() for entry in entries]

    def list_tags(self) -> List[str]:
        """Return a sorted, deduplicated list of all tags across all tools."""
        tags: set[str] = set()
        for entry in self._tools.values():
            tags.update(entry.tags)
        return sorted(tags)

    def __len__(self) -> int:
        return len(self._tools)


def build_registry() -> ToolRegistry:
    """
    Instantiate and populate the global ToolRegistry with all built-in tools.

    Adding a new tool: import its module here and call ``registry.register()``.
    No other file needs to change.
    """
    from tools.terraform import apply, destroy, plan, init, validate, output, state_list
    from tools.github import (
        create_pr, get_repo, list_issues, trigger_workflow, create_release,
        create_issue, merge_pr, get_workflow_run,
    )
    from tools.aws import ec2, s3, lambda_tools, rds, ec2_lifecycle, s3_objects, cloudwatch, secrets, networking
    from tools.kubernetes import (
        deploy,
        get_pods,
        get_logs,
        get_events,
        scale,
        rollout_restart,
        rollout_status,
        get_deployments,
        get_services,
        get_nodes,
        delete_pod,
    )
    from tools.helm import helm_tools
    from tools.azure import azure_tools
    from tools.gcp import gcp_tools

    registry = ToolRegistry()

    # ── Terraform ──────────────────────────────────────────────────────────
    registry.register(ToolEntry(
        name=plan.TOOL_NAME,
        description=plan.TOOL_DESCRIPTION,
        input_schema=plan.TOOL_INPUT_SCHEMA,
        handler=plan.handler,
        tags=["terraform", "iac"],
    ))
    registry.register(ToolEntry(
        name=apply.TOOL_NAME,
        description=apply.TOOL_DESCRIPTION,
        input_schema=apply.TOOL_INPUT_SCHEMA,
        handler=apply.handler,
        tags=["terraform", "iac"],
    ))
    registry.register(ToolEntry(
        name=destroy.TOOL_NAME,
        description=destroy.TOOL_DESCRIPTION,
        input_schema=destroy.TOOL_INPUT_SCHEMA,
        handler=destroy.handler,
        tags=["terraform", "iac", "destructive"],
    ))
    registry.register(ToolEntry(
        name=init.TOOL_NAME,
        description=init.TOOL_DESCRIPTION,
        input_schema=init.TOOL_INPUT_SCHEMA,
        handler=init.handler,
        tags=["terraform", "iac"],
    ))
    registry.register(ToolEntry(
        name=validate.TOOL_NAME,
        description=validate.TOOL_DESCRIPTION,
        input_schema=validate.TOOL_INPUT_SCHEMA,
        handler=validate.handler,
        tags=["terraform", "iac"],
    ))
    registry.register(ToolEntry(
        name=output.TOOL_NAME,
        description=output.TOOL_DESCRIPTION,
        input_schema=output.TOOL_INPUT_SCHEMA,
        handler=output.handler,
        tags=["terraform", "iac"],
    ))
    registry.register(ToolEntry(
        name=state_list.TOOL_NAME,
        description=state_list.TOOL_DESCRIPTION,
        input_schema=state_list.TOOL_INPUT_SCHEMA,
        handler=state_list.handler,
        tags=["terraform", "iac"],
    ))

    # ── GitHub ─────────────────────────────────────────────────────────────
    registry.register(ToolEntry(
        name=create_pr.TOOL_NAME,
        description=create_pr.TOOL_DESCRIPTION,
        input_schema=create_pr.TOOL_INPUT_SCHEMA,
        handler=create_pr.handler,
        tags=["github", "scm"],
    ))
    registry.register(ToolEntry(
        name=get_repo.TOOL_NAME,
        description=get_repo.TOOL_DESCRIPTION,
        input_schema=get_repo.TOOL_INPUT_SCHEMA,
        handler=get_repo.handler,
        tags=["github", "scm"],
    ))
    registry.register(ToolEntry(
        name=list_issues.TOOL_NAME,
        description=list_issues.TOOL_DESCRIPTION,
        input_schema=list_issues.TOOL_INPUT_SCHEMA,
        handler=list_issues.handler,
        tags=["github", "scm"],
    ))
    registry.register(ToolEntry(
        name=trigger_workflow.TOOL_NAME,
        description=trigger_workflow.TOOL_DESCRIPTION,
        input_schema=trigger_workflow.TOOL_INPUT_SCHEMA,
        handler=trigger_workflow.handler,
        tags=["github", "scm", "ci"],
    ))
    registry.register(ToolEntry(
        name=create_release.TOOL_NAME,
        description=create_release.TOOL_DESCRIPTION,
        input_schema=create_release.TOOL_INPUT_SCHEMA,
        handler=create_release.handler,
        tags=["github", "scm"],
    ))
    registry.register(ToolEntry(
        name=create_issue.TOOL_NAME,
        description=create_issue.TOOL_DESCRIPTION,
        input_schema=create_issue.TOOL_INPUT_SCHEMA,
        handler=create_issue.handler,
        tags=["github", "scm"],
    ))
    registry.register(ToolEntry(
        name=merge_pr.TOOL_NAME,
        description=merge_pr.TOOL_DESCRIPTION,
        input_schema=merge_pr.TOOL_INPUT_SCHEMA,
        handler=merge_pr.handler,
        tags=["github", "scm"],
    ))
    registry.register(ToolEntry(
        name=get_workflow_run.TOOL_NAME,
        description=get_workflow_run.TOOL_DESCRIPTION,
        input_schema=get_workflow_run.TOOL_INPUT_SCHEMA,
        handler=get_workflow_run.handler,
        tags=["github", "scm", "ci"],
    ))

    # ── AWS ────────────────────────────────────────────────────────────────
    registry.register(ToolEntry(
        name=ec2.TOOL_NAME,
        description=ec2.TOOL_DESCRIPTION,
        input_schema=ec2.TOOL_INPUT_SCHEMA,
        handler=ec2.handler,
        tags=["aws", "ec2", "compute"],
    ))
    registry.register(ToolEntry(
        name=ec2.LIST_TOOL_NAME,
        description=ec2.LIST_TOOL_DESCRIPTION,
        input_schema=ec2.LIST_TOOL_INPUT_SCHEMA,
        handler=ec2.list_handler,
        tags=["aws", "ec2", "compute"],
    ))
    registry.register(ToolEntry(
        name=s3.TOOL_NAME,
        description=s3.TOOL_DESCRIPTION,
        input_schema=s3.TOOL_INPUT_SCHEMA,
        handler=s3.handler,
        tags=["aws", "s3", "storage"],
    ))
    registry.register(ToolEntry(
        name=s3.LIST_TOOL_NAME,
        description=s3.LIST_TOOL_DESCRIPTION,
        input_schema=s3.LIST_TOOL_INPUT_SCHEMA,
        handler=s3.list_handler,
        tags=["aws", "s3", "storage"],
    ))
    registry.register(ToolEntry(
        name=lambda_tools.TOOL_NAME,
        description=lambda_tools.TOOL_DESCRIPTION,
        input_schema=lambda_tools.TOOL_INPUT_SCHEMA,
        handler=lambda_tools.handler,
        tags=["aws", "lambda", "serverless"],
    ))
    registry.register(ToolEntry(
        name=lambda_tools.INVOKE_TOOL_NAME,
        description=lambda_tools.INVOKE_TOOL_DESCRIPTION,
        input_schema=lambda_tools.INVOKE_TOOL_INPUT_SCHEMA,
        handler=lambda_tools.invoke_handler,
        tags=["aws", "lambda", "serverless"],
        timeout_seconds=300,  # Lambda max timeout is 15 min; we cap at 5
    ))
    registry.register(ToolEntry(
        name=rds.TOOL_NAME,
        description=rds.TOOL_DESCRIPTION,
        input_schema=rds.TOOL_INPUT_SCHEMA,
        handler=rds.handler,
        tags=["aws", "rds", "database"],
    ))
    # EC2 lifecycle
    registry.register(ToolEntry(
        name=ec2_lifecycle.STOP_TOOL_NAME,
        description=ec2_lifecycle.STOP_TOOL_DESCRIPTION,
        input_schema=ec2_lifecycle.STOP_TOOL_INPUT_SCHEMA,
        handler=ec2_lifecycle.stop_handler,
        tags=["aws", "ec2", "compute"],
    ))
    registry.register(ToolEntry(
        name=ec2_lifecycle.START_TOOL_NAME,
        description=ec2_lifecycle.START_TOOL_DESCRIPTION,
        input_schema=ec2_lifecycle.START_TOOL_INPUT_SCHEMA,
        handler=ec2_lifecycle.start_handler,
        tags=["aws", "ec2", "compute"],
    ))
    registry.register(ToolEntry(
        name=ec2_lifecycle.TERMINATE_TOOL_NAME,
        description=ec2_lifecycle.TERMINATE_TOOL_DESCRIPTION,
        input_schema=ec2_lifecycle.TERMINATE_TOOL_INPUT_SCHEMA,
        handler=ec2_lifecycle.terminate_handler,
        tags=["aws", "ec2", "compute", "destructive"],
    ))
    # S3 objects
    registry.register(ToolEntry(
        name=s3_objects.TOOL_NAME,
        description=s3_objects.TOOL_DESCRIPTION,
        input_schema=s3_objects.TOOL_INPUT_SCHEMA,
        handler=s3_objects.handler,
        tags=["aws", "s3", "storage"],
    ))
    # CloudWatch
    registry.register(ToolEntry(
        name=cloudwatch.GET_METRICS_TOOL_NAME,
        description=cloudwatch.GET_METRICS_TOOL_DESCRIPTION,
        input_schema=cloudwatch.GET_METRICS_TOOL_INPUT_SCHEMA,
        handler=cloudwatch.get_metrics_handler,
        tags=["aws", "cloudwatch", "observability"],
    ))
    registry.register(ToolEntry(
        name=cloudwatch.ALARMS_TOOL_NAME,
        description=cloudwatch.ALARMS_TOOL_DESCRIPTION,
        input_schema=cloudwatch.ALARMS_TOOL_INPUT_SCHEMA,
        handler=cloudwatch.alarms_handler,
        tags=["aws", "cloudwatch", "observability"],
    ))
    registry.register(ToolEntry(
        name=cloudwatch.LOG_GROUPS_TOOL_NAME,
        description=cloudwatch.LOG_GROUPS_TOOL_DESCRIPTION,
        input_schema=cloudwatch.LOG_GROUPS_TOOL_INPUT_SCHEMA,
        handler=cloudwatch.log_groups_handler,
        tags=["aws", "cloudwatch", "observability", "logs"],
    ))
    registry.register(ToolEntry(
        name=cloudwatch.QUERY_LOGS_TOOL_NAME,
        description=cloudwatch.QUERY_LOGS_TOOL_DESCRIPTION,
        input_schema=cloudwatch.QUERY_LOGS_TOOL_INPUT_SCHEMA,
        handler=cloudwatch.query_logs_handler,
        tags=["aws", "cloudwatch", "observability", "logs"],
        timeout_seconds=60,
    ))
    # Secrets / SSM
    registry.register(ToolEntry(
        name=secrets.SECRETS_GET_TOOL_NAME,
        description=secrets.SECRETS_GET_TOOL_DESCRIPTION,
        input_schema=secrets.SECRETS_GET_TOOL_INPUT_SCHEMA,
        handler=secrets.secrets_get_handler,
        tags=["aws", "secrets", "security"],
    ))
    registry.register(ToolEntry(
        name=secrets.SECRETS_CREATE_TOOL_NAME,
        description=secrets.SECRETS_CREATE_TOOL_DESCRIPTION,
        input_schema=secrets.SECRETS_CREATE_TOOL_INPUT_SCHEMA,
        handler=secrets.secrets_create_handler,
        tags=["aws", "secrets", "security"],
    ))
    registry.register(ToolEntry(
        name=secrets.SSM_GET_TOOL_NAME,
        description=secrets.SSM_GET_TOOL_DESCRIPTION,
        input_schema=secrets.SSM_GET_TOOL_INPUT_SCHEMA,
        handler=secrets.ssm_get_handler,
        tags=["aws", "ssm", "config"],
    ))
    registry.register(ToolEntry(
        name=secrets.SSM_PUT_TOOL_NAME,
        description=secrets.SSM_PUT_TOOL_DESCRIPTION,
        input_schema=secrets.SSM_PUT_TOOL_INPUT_SCHEMA,
        handler=secrets.ssm_put_handler,
        tags=["aws", "ssm", "config"],
    ))
    # Networking
    registry.register(ToolEntry(
        name=networking.VPC_LIST_TOOL_NAME,
        description=networking.VPC_LIST_TOOL_DESCRIPTION,
        input_schema=networking.VPC_LIST_TOOL_INPUT_SCHEMA,
        handler=networking.vpc_list_handler,
        tags=["aws", "networking", "vpc"],
    ))
    registry.register(ToolEntry(
        name=networking.SG_LIST_TOOL_NAME,
        description=networking.SG_LIST_TOOL_DESCRIPTION,
        input_schema=networking.SG_LIST_TOOL_INPUT_SCHEMA,
        handler=networking.sg_list_handler,
        tags=["aws", "networking", "security"],
    ))
    registry.register(ToolEntry(
        name=networking.R53_TOOL_NAME,
        description=networking.R53_TOOL_DESCRIPTION,
        input_schema=networking.R53_TOOL_INPUT_SCHEMA,
        handler=networking.r53_list_handler,
        tags=["aws", "networking", "dns"],
    ))

    # ── Kubernetes ─────────────────────────────────────────────────────────
    registry.register(ToolEntry(
        name=deploy.TOOL_NAME,
        description=deploy.TOOL_DESCRIPTION,
        input_schema=deploy.TOOL_INPUT_SCHEMA,
        handler=deploy.handler,
        tags=["kubernetes", "k8s", "deployment"],
    ))
    registry.register(ToolEntry(
        name=get_pods.TOOL_NAME,
        description=get_pods.TOOL_DESCRIPTION,
        input_schema=get_pods.TOOL_INPUT_SCHEMA,
        handler=get_pods.handler,
        tags=["kubernetes", "k8s"],
    ))
    registry.register(ToolEntry(
        name=get_logs.TOOL_NAME,
        description=get_logs.TOOL_DESCRIPTION,
        input_schema=get_logs.TOOL_INPUT_SCHEMA,
        handler=get_logs.handler,
        tags=["kubernetes", "k8s", "debug"],
    ))
    registry.register(ToolEntry(
        name=get_events.TOOL_NAME,
        description=get_events.TOOL_DESCRIPTION,
        input_schema=get_events.TOOL_INPUT_SCHEMA,
        handler=get_events.handler,
        tags=["kubernetes", "k8s", "debug"],
    ))
    registry.register(ToolEntry(
        name=scale.TOOL_NAME,
        description=scale.TOOL_DESCRIPTION,
        input_schema=scale.TOOL_INPUT_SCHEMA,
        handler=scale.handler,
        tags=["kubernetes", "k8s", "deployment"],
    ))
    registry.register(ToolEntry(
        name=rollout_restart.TOOL_NAME,
        description=rollout_restart.TOOL_DESCRIPTION,
        input_schema=rollout_restart.TOOL_INPUT_SCHEMA,
        handler=rollout_restart.handler,
        tags=["kubernetes", "k8s", "deployment"],
    ))
    registry.register(ToolEntry(
        name=rollout_status.TOOL_NAME,
        description=rollout_status.TOOL_DESCRIPTION,
        input_schema=rollout_status.TOOL_INPUT_SCHEMA,
        handler=rollout_status.handler,
        tags=["kubernetes", "k8s", "deployment"],
    ))
    registry.register(ToolEntry(
        name=get_deployments.TOOL_NAME,
        description=get_deployments.TOOL_DESCRIPTION,
        input_schema=get_deployments.TOOL_INPUT_SCHEMA,
        handler=get_deployments.handler,
        tags=["kubernetes", "k8s", "deployment"],
    ))
    registry.register(ToolEntry(
        name=get_services.TOOL_NAME,
        description=get_services.TOOL_DESCRIPTION,
        input_schema=get_services.TOOL_INPUT_SCHEMA,
        handler=get_services.handler,
        tags=["kubernetes", "k8s", "networking"],
    ))
    registry.register(ToolEntry(
        name=get_nodes.TOOL_NAME,
        description=get_nodes.TOOL_DESCRIPTION,
        input_schema=get_nodes.TOOL_INPUT_SCHEMA,
        handler=get_nodes.handler,
        tags=["kubernetes", "k8s", "cluster"],
    ))
    registry.register(ToolEntry(
        name=delete_pod.TOOL_NAME,
        description=delete_pod.TOOL_DESCRIPTION,
        input_schema=delete_pod.TOOL_INPUT_SCHEMA,
        handler=delete_pod.handler,
        tags=["kubernetes", "k8s", "debug"],
    ))

    # ── Helm ───────────────────────────────────────────────────────────────
    registry.register(ToolEntry(
        name=helm_tools.LIST_TOOL_NAME,
        description=helm_tools.LIST_TOOL_DESCRIPTION,
        input_schema=helm_tools.LIST_TOOL_INPUT_SCHEMA,
        handler=helm_tools.list_handler,
        tags=["helm", "kubernetes", "k8s"],
    ))
    registry.register(ToolEntry(
        name=helm_tools.INSTALL_TOOL_NAME,
        description=helm_tools.INSTALL_TOOL_DESCRIPTION,
        input_schema=helm_tools.INSTALL_TOOL_INPUT_SCHEMA,
        handler=helm_tools.install_handler,
        tags=["helm", "kubernetes", "k8s"],
        timeout_seconds=300,
    ))
    registry.register(ToolEntry(
        name=helm_tools.UPGRADE_TOOL_NAME,
        description=helm_tools.UPGRADE_TOOL_DESCRIPTION,
        input_schema=helm_tools.UPGRADE_TOOL_INPUT_SCHEMA,
        handler=helm_tools.upgrade_handler,
        tags=["helm", "kubernetes", "k8s"],
        timeout_seconds=300,
    ))
    registry.register(ToolEntry(
        name=helm_tools.ROLLBACK_TOOL_NAME,
        description=helm_tools.ROLLBACK_TOOL_DESCRIPTION,
        input_schema=helm_tools.ROLLBACK_TOOL_INPUT_SCHEMA,
        handler=helm_tools.rollback_handler,
        tags=["helm", "kubernetes", "k8s"],
        timeout_seconds=300,
    ))
    registry.register(ToolEntry(
        name=helm_tools.STATUS_TOOL_NAME,
        description=helm_tools.STATUS_TOOL_DESCRIPTION,
        input_schema=helm_tools.STATUS_TOOL_INPUT_SCHEMA,
        handler=helm_tools.status_handler,
        tags=["helm", "kubernetes", "k8s"],
    ))

    # ── Azure ──────────────────────────────────────────────────────────────
    registry.register(ToolEntry(
        name=azure_tools.RG_LIST_TOOL_NAME,
        description=azure_tools.RG_LIST_TOOL_DESCRIPTION,
        input_schema=azure_tools.RG_LIST_TOOL_INPUT_SCHEMA,
        handler=azure_tools.rg_list_handler,
        tags=["azure", "cloud", "multicloud"],
    ))
    registry.register(ToolEntry(
        name=azure_tools.VM_LIST_TOOL_NAME,
        description=azure_tools.VM_LIST_TOOL_DESCRIPTION,
        input_schema=azure_tools.VM_LIST_TOOL_INPUT_SCHEMA,
        handler=azure_tools.vm_list_handler,
        tags=["azure", "cloud", "compute", "multicloud"],
    ))
    registry.register(ToolEntry(
        name=azure_tools.VM_START_TOOL_NAME,
        description=azure_tools.VM_START_TOOL_DESCRIPTION,
        input_schema=azure_tools.VM_START_TOOL_INPUT_SCHEMA,
        handler=azure_tools.vm_start_handler,
        tags=["azure", "cloud", "compute", "multicloud"],
        timeout_seconds=360,
    ))
    registry.register(ToolEntry(
        name=azure_tools.VM_STOP_TOOL_NAME,
        description=azure_tools.VM_STOP_TOOL_DESCRIPTION,
        input_schema=azure_tools.VM_STOP_TOOL_INPUT_SCHEMA,
        handler=azure_tools.vm_stop_handler,
        tags=["azure", "cloud", "compute", "multicloud"],
        timeout_seconds=360,
    ))

    # ── GCP ────────────────────────────────────────────────────────────────
    registry.register(ToolEntry(
        name=gcp_tools.INSTANCES_TOOL_NAME,
        description=gcp_tools.INSTANCES_TOOL_DESCRIPTION,
        input_schema=gcp_tools.INSTANCES_TOOL_INPUT_SCHEMA,
        handler=gcp_tools.instances_handler,
        tags=["gcp", "cloud", "compute", "multicloud"],
    ))
    registry.register(ToolEntry(
        name=gcp_tools.BUCKETS_TOOL_NAME,
        description=gcp_tools.BUCKETS_TOOL_DESCRIPTION,
        input_schema=gcp_tools.BUCKETS_TOOL_INPUT_SCHEMA,
        handler=gcp_tools.buckets_handler,
        tags=["gcp", "cloud", "storage", "multicloud"],
    ))
    registry.register(ToolEntry(
        name=gcp_tools.GKE_TOOL_NAME,
        description=gcp_tools.GKE_TOOL_DESCRIPTION,
        input_schema=gcp_tools.GKE_TOOL_INPUT_SCHEMA,
        handler=gcp_tools.gke_handler,
        tags=["gcp", "cloud", "kubernetes", "multicloud"],
    ))

    log.info("registry_built", total_tools=len(registry))
    return registry
