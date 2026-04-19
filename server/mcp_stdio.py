"""
server/mcp_stdio.py
-------------------
MCP stdio entry point for Claude Desktop integration.

Claude Desktop launches this as a subprocess and communicates via
stdin/stdout using the Model Context Protocol (MCP).

All DevOps tools are registered and proxied through the existing
ToolRegistry + ToolExecutor stack — identical logic to the HTTP server,
just with a different transport layer.

Uses the low-level mcp.server.Server public API so the tool JSON schemas
are passed explicitly — no fragile introspection of **kwargs signatures.

Usage (in claude_desktop_config.json):
    {
      "mcpServers": {
        "devops-mcp": {
          "command": "/path/to/python",
          "args": ["-m", "server.mcp_stdio"],
          "cwd": "/path/to/devops-mcp-server"
        }
      }
    }
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from server.registry import build_registry
from core.executor import ToolExecutor

# ── Bootstrap ─────────────────────────────────────────────────────────────────

registry = build_registry()
executor = ToolExecutor(registry)
server = Server("devops-mcp-server")

# ── Tool listing ──────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Return all registered tools with their full JSON schemas."""
    return [
        types.Tool(
            name=entry.name,
            description=entry.description,
            inputSchema=entry.input_schema,
        )
        for entry in registry.list_all()
    ]

# ── Tool execution ────────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Dispatch a tool call through the existing executor stack."""
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None, lambda: executor.execute_safe(name, arguments or {})
    )
    if response.status == "success":
        text = json.dumps(response.data, indent=2, default=str)
    else:
        text = f"ERROR: {response.error}"
    return [types.TextContent(type="text", text=text)]

# ── Entry point ───────────────────────────────────────────────────────────────

async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(_run())
