"""
core/config.py
--------------
Centralised environment configuration using pydantic-settings.
All settings are loaded from environment variables (or a .env file).
"""

from __future__ import annotations

import os
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

    # ── Server ───────────────────────────────────────────────────────────────
    server_host: str = Field(default="0.0.0.0", env="SERVER_HOST")
    server_port: int = Field(default=8000, env="SERVER_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    dry_run: bool = Field(default=False, env="DRY_RUN")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
