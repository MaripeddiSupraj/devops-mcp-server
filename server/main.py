"""
server/main.py
--------------
FastAPI application — the HTTP entry point for the MCP DevOps server.

Endpoints:
    GET  /health               Liveness probe
    GET  /tools                List all registered tools
    POST /tools/execute        Execute a tool by name
    GET  /tools/{tool_name}    Describe a single tool
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.executor import ToolExecutor
from core.logger import get_logger
from server.registry import build_registry
from server.schemas import (
    HealthResponse,
    ToolCallRequest,
    ToolListResponse,
    ToolDefinition,
    ToolResponse,
)

log = get_logger(__name__)

# ── Bootstrap ────────────────────────────────────────────────────────────────

settings = get_settings()
registry = build_registry()
executor = ToolExecutor(registry)

# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="DevOps MCP Server",
    description=(
        "Model Context Protocol server exposing DevOps automation tools "
        "(Terraform, GitHub, AWS, Kubernetes) as structured JSON endpoints "
        "consumable by AI agents such as LangGraph."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Meta"])
async def health_check() -> HealthResponse:
    """Liveness probe — returns 200 OK when the server is running."""
    return HealthResponse(tools_registered=len(registry))


@app.get("/tools", response_model=ToolListResponse, tags=["Tools"])
async def list_tools() -> ToolListResponse:
    """
    Return all registered MCP tool definitions.

    AI agents should call this endpoint to discover what tools are available
    before deciding which one to invoke.
    """
    definitions = registry.list_definitions()
    return ToolListResponse(tools=definitions, count=len(definitions))


@app.get("/tools/{tool_name}", response_model=ToolDefinition, tags=["Tools"])
async def describe_tool(tool_name: str) -> ToolDefinition:
    """Return the definition (name, description, schema) for a single tool."""
    entry = registry.get(tool_name)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found. "
                   f"Available tools: {registry.list_names()}",
        )
    return entry.to_definition()


@app.post("/tools/execute", response_model=ToolResponse, tags=["Tools"])
async def execute_tool(request: ToolCallRequest) -> ToolResponse:
    """
    Execute a registered tool.

    The executor validates inputs against the tool's JSON schema and
    returns a structured ``ToolResponse`` with status, data, or error.

    ### Example request body
    ```json
    {
      "tool_name": "terraform_plan",
      "inputs": {
        "path": "/tmp/terraform/my-infra",
        "dry_run": true
      }
    }
    ```

    ### Example success response
    ```json
    {
      "status": "success",
      "data": {
        "stdout": "No changes. Infrastructure is up-to-date.",
        "stderr": "",
        "exit_code": 0,
        "has_changes": false,
        "dry_run": false
      },
      "error": null
    }
    ```
    """
    log.info("execute_request", tool=request.tool_name, inputs=request.inputs)
    response = executor.execute(request.tool_name, request.inputs)
    return response


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
        log_level=settings.log_level.lower(),
    )
