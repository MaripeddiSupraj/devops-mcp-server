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
        name:         Unique tool identifier used in API calls.
        description:  Human/AI-readable description of what the tool does.
        input_schema: JSON Schema object describing accepted parameters.
        handler:      Callable that executes the tool logic.
        tags:         Optional categorisation tags (e.g. ``["terraform", "iac"]``).
    """

    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Any]
    tags: List[str] = field(default_factory=list)

    def to_definition(self) -> ToolDefinition:
        """Return a serialisable ToolDefinition (no handler callable)."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
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

    def list_definitions(self) -> List[ToolDefinition]:
        """Return ToolDefinition objects suitable for JSON serialisation."""
        return [entry.to_definition() for entry in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)


def build_registry() -> ToolRegistry:
    """
    Instantiate and populate the global ToolRegistry with all built-in tools.

    Adding a new tool: import its module here and call ``registry.register()``.
    No other file needs to change.
    """
    from tools.terraform import apply, destroy, plan
    from tools.github import create_pr, get_repo
    from tools.aws import ec2, s3
    from tools.kubernetes import deploy, get_pods

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

    log.info("registry_built", total_tools=len(registry))
    return registry
