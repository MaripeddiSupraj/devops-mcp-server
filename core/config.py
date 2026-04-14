"""
core/config.py
--------------
Centralised environment configuration using pydantic-settings.
All settings are loaded from environment variables (or a .env file).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration pulled from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── GitHub ──────────────────────────────────────────────────────────────
    github_token: Optional[str] = Field(default=None, env="GITHUB_TOKEN")

    # ── AWS ─────────────────────────────────────────────────────────────────
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")

    # ── Kubernetes ───────────────────────────────────────────────────────────
    kubeconfig_path: Optional[str] = Field(default=None, env="KUBECONFIG")

    # ── Terraform ────────────────────────────────────────────────────────────
    terraform_binary: str = Field(default="terraform", env="TERRAFORM_BINARY")
    terraform_allowed_base_dir: str = Field(
        default="/tmp/terraform",
        env="TERRAFORM_ALLOWED_BASE_DIR",
        description="Root directory under which all Terraform paths must reside.",
    )
    terraform_timeout_seconds: int = Field(
        default=600,
        env="TERRAFORM_TIMEOUT_SECONDS",
        description="Maximum seconds a single Terraform command may run before being killed.",
    )

    # ── Server ───────────────────────────────────────────────────────────────
    server_host: str = Field(default="0.0.0.0", env="SERVER_HOST")
    server_port: int = Field(default=8000, env="SERVER_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    dry_run: bool = Field(default=False, env="DRY_RUN")
    api_key: Optional[str] = Field(
        default=None,
        env="MCP_API_KEY",
        description=(
            "When set, every request to /tools/* must include "
            "'Authorization: Bearer <key>' or 'X-API-Key: <key>'. "
            "Leave unset to disable auth (dev/local only)."
        ),
    )
    environment: str = Field(
        default="development",
        env="ENVIRONMENT",
        description="Runtime environment label (development | staging | production).",
    )
    cors_origins: str = Field(
        default="*",
        env="CORS_ORIGINS",
        description=(
            "Comma-separated list of allowed CORS origins. "
            "Use '*' for dev/local. Set explicit origins in production. "
            "Example: https://app.example.com,https://admin.example.com"
        ),
    )

    # ── Slack ────────────────────────────────────────────────────────────────
    slack_webhook_url: Optional[str] = Field(
        default=None,
        env="SLACK_WEBHOOK_URL",
        description="Slack incoming webhook URL. When set, tool success/failure notifications are posted.",
    )

    # ── Audit ────────────────────────────────────────────────────────────────
    audit_db_path: str = Field(
        default="audit.db",
        env="AUDIT_DB_PATH",
        description="Path to SQLite audit log database.",
    )

    # ── Tool execution ───────────────────────────────────────────────────────
    default_tool_timeout_seconds: int = Field(
        default=120,
        env="TOOL_TIMEOUT_SECONDS",
        description="Default per-tool execution timeout in seconds. 0 = no timeout.",
    )

    def cors_origins_list(self) -> list[str]:
        """Return CORS_ORIGINS parsed into a list."""
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
