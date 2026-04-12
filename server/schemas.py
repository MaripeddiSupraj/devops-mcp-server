"""
server/schemas.py
-----------------
Pydantic models used as the wire format for all MCP requests and responses.
These are the data contracts between the MCP server and its clients.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ── Inbound ──────────────────────────────────────────────────────────────────

class ToolCallRequest(BaseModel):
    """Payload sent by an AI agent to invoke a specific tool."""

    tool_name: str = Field(..., description="Registered name of the tool to execute.")
    inputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value arguments matching the tool's input_schema.",
    )


# ── Outbound ─────────────────────────────────────────────────────────────────

class ToolResponse(BaseModel):
    """Uniform response envelope returned by every tool execution."""

    status: Literal["success", "error"] = Field(
        ..., description="'success' if execution completed without exception, 'error' otherwise."
    )
    data: Optional[Any] = Field(
        default=None,
        description="Tool output on success. Structure depends on the individual tool.",
    )
    error: Optional[str] = Field(
        default=None,
        description="Human-readable error message when status='error'.",
    )


class ToolDefinition(BaseModel):
    """Describes a single registered MCP tool (returned by the list endpoint)."""

    name: str
    description: str
    input_schema: Dict[str, Any]


class ToolListResponse(BaseModel):
    """Response from the tools/list endpoint."""

    tools: List[ToolDefinition]
    count: int = Field(..., description="Total number of registered tools.")


# ── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Liveness/readiness probe response."""

    status: Literal["ok"] = "ok"
    version: str = "1.0.0"
    tools_registered: int = 0
