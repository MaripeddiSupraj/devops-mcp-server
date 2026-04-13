"""
core/security.py
----------------
API key authentication for the MCP server.

When MCP_API_KEY is set in the environment, every request to /tools/*
must supply the key via one of:
    Authorization: Bearer <key>
    X-API-Key: <key>

When MCP_API_KEY is NOT set, auth is disabled entirely — suitable for
local development only. Attempting to run without an API key in production
will trigger a startup warning via core/startup.py.

Usage (FastAPI dependency):
    @app.post("/tools/execute")
    async def execute_tool(request: Request, _: None = Depends(verify_api_key)):
        ...
"""

from __future__ import annotations

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from core.config import get_settings
from core.logger import get_logger

log = get_logger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer = HTTPBearer(auto_error=False)


async def verify_api_key(
    request: Request,
    x_api_key: str | None = Security(_api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    """
    FastAPI dependency — enforces API key auth when MCP_API_KEY is configured.

    Accepts the key via:
      - X-API-Key: <key>            header
      - Authorization: Bearer <key> header

    Skips auth entirely when MCP_API_KEY is not set (dev mode).
    """
    settings = get_settings()
    expected = settings.api_key

    if not expected:
        # Auth disabled — dev/local mode. Startup warning is emitted separately.
        return

    # Collect the provided key from either header
    provided = x_api_key or (bearer.credentials if bearer else None)

    if not provided:
        log.warning(
            "auth_missing",
            path=str(request.url.path),
            method=request.method,
        )
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide 'X-API-Key: <key>' or 'Authorization: Bearer <key>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Constant-time comparison to prevent timing attacks
    import hmac
    if not hmac.compare_digest(provided, expected):
        log.warning(
            "auth_invalid",
            path=str(request.url.path),
            method=request.method,
        )
        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
        )
