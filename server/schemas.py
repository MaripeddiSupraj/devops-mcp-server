"""
server/schemas.py
-----------------
Pydantic models — the wire format for all MCP requests and responses.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ── Inbound ───────────────────────────────────────────────────────────────────

class ToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="Registered name of the tool to execute.")
    inputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value arguments matching the tool's input_schema.",
    )


class BatchToolCallRequest(BaseModel):
    tool_name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    call_id: Optional[str] = Field(
        default=None,
        description="Caller-supplied identifier echoed back in the response.",
    )


class BatchExecuteRequest(BaseModel):
    calls: List[BatchToolCallRequest] = Field(
        ..., description="Ordered list of tool calls to execute (max 20)."
    )


class SubmitJobRequest(BaseModel):
    tool_name: str = Field(..., description="Registered name of the tool to execute.")
    inputs: Dict[str, Any] = Field(default_factory=dict)


# ── Outbound ──────────────────────────────────────────────────────────────────

class ToolResponse(BaseModel):
    status: Literal["success", "error"]
    data: Optional[Any] = None
    error: Optional[str] = None
    request_id: Optional[str] = None


class BatchToolResult(BaseModel):
    call_id: Optional[str] = None
    tool_name: str
    status: Literal["success", "error"]
    data: Optional[Any] = None
    error: Optional[str] = None


class BatchExecuteResponse(BaseModel):
    results: List[BatchToolResult]
    total: int
    succeeded: int
    failed: int
    request_id: Optional[str] = None


class SubmitJobResponse(BaseModel):
    job_id: str
    tool_name: str
    status: Literal["pending"]
    poll_url: str


class JobResponse(BaseModel):
    job_id: str
    tool_name: str
    status: Literal["pending", "running", "success", "error"]
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    tags: List[str] = Field(default_factory=list)


class ToolListResponse(BaseModel):
    tools: List[ToolDefinition]
    count: int


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"] = "ok"
    version: str = "2.0.0"
    tools_registered: int = 0
    environment: str = "development"
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal startup warnings (missing credentials, etc.).",
    )
