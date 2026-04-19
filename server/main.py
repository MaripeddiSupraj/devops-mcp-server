"""
server/main.py
--------------
Production-grade FastAPI application — HTTP entry point for the DevOps MCP server.

API surface
-----------
    GET  /health/live               Kubernetes liveness probe
    GET  /health/ready              Kubernetes readiness probe (checks creds)
    GET  /metrics                   Prometheus metrics
    GET  /tools                     List tools (supports ?tag= filter)
    GET  /tools/tags                All available tag values
    GET  /tools/{tool_name}         Describe a single tool
    POST /tools/execute             Execute a tool synchronously  (rate-limited)
    POST /tools/execute/batch       Execute up to 20 tools in one request
    POST /tools/execute/async       Submit a tool for background execution
    GET  /jobs/{job_id}             Poll background job status

Production features
-------------------
    Security      API key auth via X-API-Key or Authorization: Bearer
    Rate limiting 60 req/min on /execute, 20/min on /batch (slowapi)
    Tracing       X-Request-ID on every request — injected into all log lines
    Metrics       Prometheus counters/histograms via /metrics
    Probes        /health/live (process up) + /health/ready (deps configured)
    Background    Long-running tools submit as jobs; clients poll /jobs/{id}
    Tag filtering GET /tools?tag=kubernetes returns only matching tools
    Startup check Missing credentials surfaced immediately at /health/ready
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional

import structlog
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from core.config import get_settings
from core.executor import InputValidationError, ToolNotFoundError
from core.executor import ToolExecutor
from core.logger import get_logger
from core.security import verify_api_key
from core.startup import collect_startup_warnings
from core.audit import audit_log
from server.jobs import JobStore, job_store, run_job, start_cleanup_task
from server.registry import build_registry
from server.schemas import (
    AuditEntry,
    AuditResponse,
    BatchExecuteRequest,
    BatchExecuteResponse,
    BatchToolResult,
    HealthResponse,
    JobResponse,
    SubmitJobRequest,
    SubmitJobResponse,
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

# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = start_cleanup_task()
    yield
    task.cancel()

# ── Rate limiter ──────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    lifespan=lifespan,
    title="DevOps MCP Server",
    description=(
        "**Production-grade** Model Context Protocol server exposing DevOps automation tools "
        "(Terraform, GitHub, AWS, Kubernetes) as structured JSON endpoints "
        "consumable by AI agents.\n\n"
        "### Authentication\n"
        "Set `MCP_API_KEY` to enable API key auth. "
        "Pass the key via `X-API-Key: <key>` or `Authorization: Bearer <key>`.\n\n"
        "### Features\n"
        "- Tag-based tool filtering (`GET /tools?tag=kubernetes`)\n"
        "- Batch execution (`POST /tools/execute/batch`, max 20)\n"
        "- Async background jobs (`POST /tools/execute/async` + `GET /jobs/{id}`)\n"
        "- Prometheus metrics at `/metrics`\n"
        "- Kubernetes-native split health probes (`/health/live`, `/health/ready`)\n"
        "- Per-request UUID tracing (`X-Request-ID` header)\n"
        "- Rate limiting (60 req/min on execute, 20/min on batch)\n"
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """
    Attach a UUID to every request for end-to-end tracing.

    Uses X-Request-ID from the caller when provided; generates one otherwise.
    Injects into structlog context so all log lines carry the same request_id.
    Echoes back in X-Request-ID response header.
    """
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add standard security headers to every response."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Environment"] = settings.environment
    return response


# ── Prometheus metrics ────────────────────────────────────────────────────────

Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    excluded_handlers=["/health/live", "/health/ready", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


# ── Health probes ─────────────────────────────────────────────────────────────

@app.get(
    "/health/live",
    tags=["Health"],
    summary="Liveness probe",
    response_model=dict,
)
async def liveness() -> dict:
    """
    Kubernetes liveness probe — returns 200 when the process is alive.
    Should never return 5xx (that would trigger a pod restart).
    """
    return {"status": "ok", "version": "2.0.0"}


@app.get(
    "/health/ready",
    tags=["Health"],
    summary="Readiness probe",
    response_model=HealthResponse,
)
async def readiness() -> HealthResponse:
    """
    Kubernetes readiness probe.

    - **200 ok**       All credentials configured, all tools available.
    - **200 degraded** Some integrations are unconfigured (advisory warnings).
                       The pod still receives traffic — tools for other
                       integrations work fine.
    - **503**          No tools registered (server is fundamentally broken).
    """
    no_tools = len(registry) == 0
    response = HealthResponse(
        status="degraded" if _startup_warnings else "ok",
        tools_registered=len(registry),
        warnings=_startup_warnings,
        environment=settings.environment,
    )
    if no_tools:
        return JSONResponse(status_code=503, content=response.model_dump())
    return response


# Legacy /health alias — kept for backwards compatibility
@app.get("/health", include_in_schema=False)
async def health_alias():
    return await readiness()


# ── Tool endpoints ────────────────────────────────────────────────────────────

@app.get("/tools/tags", response_model=List[str], tags=["Tools"])
async def list_tags() -> List[str]:
    """Return all available tool tag values (e.g. ``kubernetes``, ``aws``)."""
    return registry.list_tags()


@app.get("/tools", response_model=ToolListResponse, tags=["Tools"])
async def list_tools(tag: Optional[str] = None) -> ToolListResponse:
    """
    Return registered MCP tool definitions.

    **Query params:**
    - ``tag`` — filter by tag: ``?tag=kubernetes``, ``?tag=aws``, ``?tag=destructive``
    """
    definitions = registry.list_definitions(tag=tag)
    return ToolListResponse(tools=definitions, count=len(definitions))


@app.get(
    "/tools/{tool_name}",
    response_model=ToolDefinition,
    tags=["Tools"],
    responses={404: {"description": "Tool not found"}},
)
async def describe_tool(tool_name: str) -> ToolDefinition:
    """Return the full definition (name, description, schema, tags) for a single tool."""
    entry = registry.get(tool_name)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found. "
                   f"Available tools: {registry.list_names()}",
        )
    return entry.to_definition()


@app.post(
    "/tools/execute",
    response_model=ToolResponse,
    tags=["Tools"],
    responses={
        400: {"description": "Input validation error"},
        401: {"description": "Missing API key"},
        403: {"description": "Invalid API key"},
        404: {"description": "Tool not found"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("60/minute")
async def execute_tool(
    request: Request,
    body: ToolCallRequest,
    _auth: None = Depends(verify_api_key),
) -> ToolResponse:
    """
    Execute a registered tool synchronously.

    Rate-limited to **60 calls / minute per IP**.
    Requires API key when ``MCP_API_KEY`` is set.

    Returns appropriate HTTP status codes:
    - **200** success or tool-level error (tool ran, but returned an error)
    - **400** input validation failed
    - **404** tool not found
    - **429** rate limit exceeded
    """
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    log.info("execute_request", tool=body.tool_name, inputs=body.inputs)

    # Build a safe hint from the API key for the audit log
    raw_key = (
        request.headers.get("X-API-Key")
        or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    )
    api_key_hint = (raw_key[:8] + "…") if raw_key else "anonymous"

    try:
        response = executor.execute(body.tool_name, body.inputs, api_key_hint=api_key_hint)
    except ToolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InputValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    response.request_id = request_id
    return response


@app.post(
    "/tools/execute/batch",
    response_model=BatchExecuteResponse,
    tags=["Tools"],
    responses={
        401: {"description": "Missing API key"},
        403: {"description": "Invalid API key"},
        422: {"description": "Batch exceeds 20-call limit"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("20/minute")
async def execute_batch(
    request: Request,
    body: BatchExecuteRequest,
    _auth: None = Depends(verify_api_key),
) -> BatchExecuteResponse:
    """
    Execute **multiple tools in a single HTTP round-trip** (max 20).

    Rate-limited to **20 batch requests / minute per IP**.
    Individual call failures do NOT abort the batch — all results always returned.
    """
    request_id = structlog.contextvars.get_contextvars().get("request_id")

    if len(body.calls) > 20:
        raise HTTPException(
            status_code=422,
            detail="Batch size exceeds maximum of 20 calls per request.",
        )

    log.info("batch_execute_request", count=len(body.calls))

    loop = asyncio.get_event_loop()

    async def _run_one(call):
        resp = await loop.run_in_executor(
            None, lambda: executor.execute_safe(call.tool_name, call.inputs)
        )
        return BatchToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            status=resp.status,
            data=resp.data,
            error=resp.error,
        )

    results: list[BatchToolResult] = await asyncio.gather(
        *[_run_one(call) for call in body.calls]
    )

    succeeded = sum(1 for r in results if r.status == "success")
    return BatchExecuteResponse(
        results=results,
        total=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
        request_id=request_id,
    )


@app.post(
    "/tools/execute/async",
    response_model=SubmitJobResponse,
    status_code=202,
    tags=["Jobs"],
    responses={
        202: {"description": "Job accepted, poll /jobs/{job_id} for status"},
        401: {"description": "Missing API key"},
        403: {"description": "Invalid API key"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("30/minute")
async def execute_async(
    request: Request,
    body: SubmitJobRequest,
    _auth: None = Depends(verify_api_key),
) -> SubmitJobResponse:
    """
    Submit a tool for **background execution**.

    Returns immediately with a ``job_id``. Poll ``GET /jobs/{job_id}``
    for status. Ideal for long-running tools (Terraform apply/destroy).

    Job results are kept for 1 hour then evicted (max 500 concurrent jobs).
    """
    job = job_store.create(body.tool_name, body.inputs)
    asyncio.create_task(run_job(job, executor.execute_safe))
    return SubmitJobResponse(
        job_id=job.job_id,
        tool_name=body.tool_name,
        status="pending",
        poll_url=f"/jobs/{job.job_id}",
    )


@app.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    tags=["Jobs"],
    responses={
        404: {"description": "Job not found"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("120/minute")
async def get_job(
    request: Request,
    job_id: str,
    _auth: None = Depends(verify_api_key),
) -> JobResponse:
    """
    Poll the status of a background job submitted via ``POST /tools/execute/async``.

    Possible ``status`` values: ``pending`` → ``running`` → ``success`` | ``error``
    """
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found. It may have expired (TTL: 1 hour).",
        )
    return JobResponse(**job.to_dict())


# ── Audit log endpoint ────────────────────────────────────────────────────────

@app.get(
    "/audit",
    response_model=AuditResponse,
    tags=["Audit"],
    summary="Recent tool invocations",
    responses={
        401: {"description": "Missing API key"},
        403: {"description": "Invalid API key"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("30/minute")
async def get_audit_log(
    request: Request,
    limit: int = 100,
    _auth: None = Depends(verify_api_key),
) -> AuditResponse:
    """
    Return the most recent tool invocations from the audit log.

    Includes tool name, status, duration, timestamp, and a masked API key hint.
    Protected by the same API key auth as the execute endpoints.

    **Query params:**
    - ``limit`` — number of entries to return (default 100, max 500)
    """
    limit = min(limit, 500)
    rows = audit_log.recent(limit=limit)
    return AuditResponse(
        entries=[AuditEntry(**row) for row in rows],
        count=len(rows),
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
