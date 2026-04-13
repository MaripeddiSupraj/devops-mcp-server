"""
server/mcp_stdio.py
-------------------
MCP stdio entry point for Claude Desktop integration.

Claude Desktop launches this as a subprocess and communicates via
stdin/stdout using the Model Context Protocol (MCP).

All 20 DevOps tools are registered and proxied through the existing
ToolRegistry + ToolExecutor stack — identical logic to the HTTP server,
just with a different transport layer.

Usage (in claude_desktop_config.json):
    {
      "mcpServers": {
        "devops-mcp": {
          "command": "/opt/anaconda3/bin/python",
          "args": ["-m", "server.mcp_stdio"],
          "cwd": "/Users/maripeddisupraj/Desktop/devops_mcp"
        }
      }
    }
"""

import json
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp import types as mcp_types

from server.registry import build_registry
from core.executor import ToolExecutor, ToolNotFoundError, InputValidationError

# ── Bootstrap ─────────────────────────────────────────────────────────────────

registry = build_registry()
executor = ToolExecutor(registry)

mcp = FastMCP(
    name="DevOps MCP Server",
    instructions=(
        "A production-grade DevOps automation server. "
        "Use these tools to manage Terraform infrastructure, GitHub repositories, "
        "AWS resources (EC2, S3), and Kubernetes clusters. "
        "Always confirm destructive operations (terraform_destroy, delete_pod) before executing."
    ),
)

# ── Register all tools dynamically from the registry ─────────────────────────

def _make_tool_fn(tool_name: str):
    """
    Build a FastMCP-compatible async function for a given tool name.
    FastMCP inspects the function signature, so we use **kwargs and
    supply the JSON schema directly via the tool decorator.
    """
    async def tool_fn(**kwargs: Any) -> str:
        response = executor.execute_safe(tool_name, kwargs)
        if response.status == "success":
            return json.dumps(response.data, indent=2, default=str)
        else:
            return f"ERROR: {response.error}"
    tool_fn.__name__ = tool_name
    return tool_fn


for entry in registry.list_all():
    fn = _make_tool_fn(entry.name)
    # Register with FastMCP using the tool's JSON schema as the parameter spec
    mcp.add_tool(
        fn,
        name=entry.name,
        description=entry.description,
        structured_output=False,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
