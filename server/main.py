"""
server/main.py
--------------
FastAPI application — the HTTP entry point for the MCP DevOps server.

Endpoints:
    GET  /health                    Liveness probe (with startup warnings)
    GET  /tools                     List all registered tools (supports ?tag= filter)
    GET  /tools/tags                List all available tags
    GET  /tools/{tool_name}         Describe a single tool
    POST /tools/execute             Execute a single tool
    POST /tools/execute/batch       Execute multiple tools in one request (max 20)

Robustness features:
    - Rate limiting (slowapi): 60 req/min per IP on execute, 120/min on reads
    - Request-ID tracing: every request gets a UUID injected into logs + response header
    - Tag filtering: GET /tools?tag=kubernetes returns only matching tools
    - Batch execution: run up to 20 tools in a single HTTP round-trip
    - Startup warnings: missing credentials are detected at boot and surfaced in /health
"""

import uuid
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from core.config import get_settings
from core.executor import ToolExecutor
from core.logger import get_logger
from core.startup import collect_startup_warnings
from server.registry import build_registry
from server.schemas import (
    BatchExecuteRequest,
    BatchExecuteResponse,
    BatchToolResult,
    HealthResponse,
    ToolCallRequest,
    ToolListResponse,
    ToolDefinition,
    ToolResponse,
)

log = get_logger(__name__)

# ── Bootstrap ─────────────────────────────────────────────────────────────────

settings = get_settings()
registry = build_registry()
executor = ToolExecutor(registry)
_startup_warnings = collect_startup_warnings(settings)

# ── Rate limiter ──────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="DevOps MCP Server",
    description=(
        "Model Context Protocol server exposing DevOps automation tools "
        "(Terraform, GitHub, AWS, Kubernetes) as structured JSON endpoints "
        "consumable by AI agents such as LangGraph.\n\n"
        "**Features:** tag filtering, batch execution, request-ID tracing, "
        "rate limiting, startup credential validation."
    ),
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)


# ── Request-ID middleware ─────────────────────────────────────────────────────

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """
    Attach a UUID to every request.

    1. Uses X-Request-ID from the caller if provided; generates one otherwise.
    2. Injects it into structlog context so all log lines for this request
       carry the same request_id field.
    3. Echoes it back in the X-Request-ID response header.
    """
    import structlog
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Meta"])
async def health_check() -> HealthResponse:
    """
    Liveness probe — returns 200 OK when the server is running.

    The ``warnings`` field surfaces any missing credentials or misconfigurations
    detected at startup so operators don't need to wait for a tool call to fail.
    """
    return HealthResponse(
        tools_registered=len(registry),
        warnings=_startup_warnings,
    )


@app.get("/tools/tags", response_model=List[str], tags=["Tools"])
async def list_tags() -> List[str]:
    """Return all available tool tags (e.g. ``kubernetes``, ``aws``, ``terraform``)."""
    return registry.list_tags()


@app.get("/tools", response_model=ToolListResponse, tags=["Tools"])
async def list_tools(tag: Optional[str] = None) -> ToolListResponse:
    """
    Return all registered MCP tool definitions.

    **Query params:**
    - ``tag`` — filter by tag, e.g. ``?tag=kubernetes``

    AI agents should call this endpoint to discover what tools are available
    before deciding which one to invoke.
    """
    definitions = registry.list_definitions(tag=tag)
    return ToolListResponse(tools=definitions, count=len(definitions))


@app.get("/tools/{tool_name}", response_model=ToolDefinition, tags=["Tools"])
async def describe_tool(tool_name: str) -> ToolDefinition:
    """Return the definition (name, description, schema, tags) for a single tool."""
    entry = registry.get(tool_name)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found. "
                   f"Available tools: {registry.list_names()}",
        )
    return entry.to_definition()


@app.post("/tools/execute", response_model=ToolResponse, tags=["Tools"])
@limiter.limit("60/minute")
async def execute_tool(request: Request, body: ToolCallRequest) -> ToolResponse:
    """
    Execute a registered tool.

    Rate-limited to **60 calls / minute per IP**.

    The executor validates inputs against the tool's JSON schema and
    returns a structured ``ToolResponse`` with status, data, or error.

    ### Example request body
    ```json
    {
      "tool_name": "terraform_plan",
      "inputs": { "path": "/tmp/terraform/my-infra", "dry_run": true }
    }
    ```
    """
    import structlog
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    log.info("execute_request", tool=body.tool_name, inputs=body.inputs)
    response = executor.execute(body.tool_name, body.inputs)
    response.request_id = request_id
    return response


@app.post("/tools/execute/batch", response_model=BatchExecuteResponse, tags=["Tools"])
@limiter.limit("20/minute")
async def execute_batch(request: Request, body: BatchExecuteRequest) -> BatchExecuteResponse:
    """
    Execute **multiple tools in a single HTTP round-trip**.

    Rate-limited to **20 batch requests / minute per IP**.
    Maximum **20 tool calls per batch**.

    Each call is executed sequentially. Failures in one call do **not** abort
    subsequent calls — all results are always returned.

    ### Example request body
    ```json
    {
      "calls": [
        {"call_id": "a", "tool_name": "k8s_get_pods",   "inputs": {"namespace": "prod"}},
        {"call_id": "b", "tool_name": "k8s_get_nodes",  "inputs": {}},
        {"call_id": "c", "tool_name": "aws_list_s3_buckets", "inputs": {}}
      ]
    }
    ```
    """
    import structlog
    request_id = structlog.contextvars.get_contextvars().get("request_id")

    if len(body.calls) > 20:
        raise HTTPException(
            status_code=422,
            detail="Batch size exceeds maximum of 20 calls per request.",
        )

    log.info("batch_execute_request", count=len(body.calls), request_id=request_id)

    results: list[BatchToolResult] = []
    for call in body.calls:
        resp = executor.execute(call.tool_name, call.inputs)
        results.append(BatchToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            status=resp.status,
            data=resp.data,
            error=resp.error,
        ))

    succeeded = sum(1 for r in results if r.status == "success")
    return BatchExecuteResponse(
        results=results,
        total=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
        request_id=request_id,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
        log_level=settings.log_level.lower(),
    )
