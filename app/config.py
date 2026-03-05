import os
from dataclasses import dataclass


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    mcp_transport: str
    github_timeout_seconds: int
    terraform_allowed_roots: list[str]
    terraform_allow_unrestricted: bool
    aws_default_cost_days: int
    aws_max_pages: int
    github_max_pages: int
    auth_enabled: bool
    auth_issuer_url: str
    auth_resource_server_url: str
    auth_required_scopes: list[str]
    auth_tokens: list[str]
    audit_enabled: bool
    terraform_apply_approval_secret: str
    terraform_apply_token_ttl_seconds: int
    terraform_apply_require_approval: bool


def load_settings() -> Settings:
    transport = os.getenv("MCP_TRANSPORT", "stdio").strip().lower() or "stdio"
    if transport not in {"stdio", "sse"}:
        transport = "stdio"

    timeout_raw = os.getenv("GITHUB_REQUEST_TIMEOUT_SECONDS", "15").strip()
    try:
        github_timeout = max(5, min(120, int(timeout_raw)))
    except ValueError:
        github_timeout = 15

    allow_unrestricted = _to_bool(os.getenv("TERRAFORM_ALLOW_UNRESTRICTED"), default=False)
    roots_raw = os.getenv("TERRAFORM_ALLOWED_ROOTS", "").strip()
    roots = [
        os.path.realpath(os.path.abspath(path.strip()))
        for path in roots_raw.split(",")
        if path.strip()
    ]

    cost_days_raw = os.getenv("AWS_DEFAULT_COST_DAYS", "30").strip()
    try:
        aws_default_cost_days = max(1, min(365, int(cost_days_raw)))
    except ValueError:
        aws_default_cost_days = 30

    aws_pages_raw = os.getenv("AWS_MAX_PAGES", "50").strip()
    try:
        aws_max_pages = max(1, min(500, int(aws_pages_raw)))
    except ValueError:
        aws_max_pages = 50

    gh_pages_raw = os.getenv("GITHUB_MAX_PAGES", "20").strip()
    try:
        github_max_pages = max(1, min(100, int(gh_pages_raw)))
    except ValueError:
        github_max_pages = 20

    auth_enabled = _to_bool(os.getenv("MCP_AUTH_ENABLED"), default=False)
    auth_issuer_url = os.getenv("MCP_AUTH_ISSUER_URL", "http://localhost:8000").strip()
    auth_resource_server_url = os.getenv("MCP_AUTH_RESOURCE_SERVER_URL", "http://localhost:8000").strip()
    scopes_raw = os.getenv("MCP_AUTH_REQUIRED_SCOPES", "").strip()
    auth_required_scopes = [s.strip() for s in scopes_raw.split(",") if s.strip()]
    auth_tokens_raw = os.getenv("MCP_AUTH_TOKENS", "").strip()
    auth_tokens = [t.strip() for t in auth_tokens_raw.split(",") if t.strip()]
    audit_enabled = _to_bool(os.getenv("MCP_AUDIT_ENABLED"), default=True)
    terraform_apply_approval_secret = os.getenv("TERRAFORM_APPLY_APPROVAL_SECRET", "").strip()
    apply_ttl_raw = os.getenv("TERRAFORM_APPLY_TOKEN_TTL_SECONDS", "300").strip()
    try:
        terraform_apply_token_ttl_seconds = max(60, min(3600, int(apply_ttl_raw)))
    except ValueError:
        terraform_apply_token_ttl_seconds = 300
    terraform_apply_require_approval = _to_bool(
        os.getenv("TERRAFORM_APPLY_REQUIRE_APPROVAL"),
        default=True,
    )

    return Settings(
        mcp_transport=transport,
        github_timeout_seconds=github_timeout,
        terraform_allowed_roots=roots,
        terraform_allow_unrestricted=allow_unrestricted,
        aws_default_cost_days=aws_default_cost_days,
        aws_max_pages=aws_max_pages,
        github_max_pages=github_max_pages,
        auth_enabled=auth_enabled,
        auth_issuer_url=auth_issuer_url,
        auth_resource_server_url=auth_resource_server_url,
        auth_required_scopes=auth_required_scopes,
        auth_tokens=auth_tokens,
        audit_enabled=audit_enabled,
        terraform_apply_approval_secret=terraform_apply_approval_secret,
        terraform_apply_token_ttl_seconds=terraform_apply_token_ttl_seconds,
        terraform_apply_require_approval=terraform_apply_require_approval,
    )


settings = load_settings()
