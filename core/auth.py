"""
core/auth.py
------------
Credential helpers — each function validates that the required credentials
are present before returning them. Raises AuthenticationError when missing.
"""

from __future__ import annotations

from typing import Tuple

from core.config import get_settings
from core.logger import get_logger

log = get_logger(__name__)


class AuthenticationError(Exception):
    """Raised when required credentials are absent or invalid."""


def get_github_token() -> str:
    """
    Return the GitHub personal-access token from environment.

    Raises:
        AuthenticationError: if GITHUB_TOKEN is not set.
    """
    token = get_settings().github_token
    if not token:
        raise AuthenticationError(
            "GITHUB_TOKEN environment variable is not set. "
            "Create a PAT at https://github.com/settings/tokens and export it."
        )
    log.debug("github_token_loaded")
    return token


def get_aws_credentials() -> Tuple[str, str, str]:
    """
    Return (access_key_id, secret_access_key, region) from environment.

    Raises:
        AuthenticationError: if AWS credentials are not set.
    """
    settings = get_settings()
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        raise AuthenticationError(
            "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must both be set. "
            "You can also use an IAM role or AWS SSO — set the variables before starting."
        )
    log.debug("aws_credentials_loaded", region=settings.aws_region)
    return settings.aws_access_key_id, settings.aws_secret_access_key, settings.aws_region


def get_azure_credentials() -> str:
    """Return the Azure subscription ID. Raises if not set."""
    sub_id = get_settings().azure_subscription_id
    if not sub_id:
        raise AuthenticationError(
            "AZURE_SUBSCRIPTION_ID is not set. "
            "Also set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET for service principal auth."
        )
    log.debug("azure_credentials_loaded", subscription=sub_id)
    return sub_id


def get_gcp_credentials() -> str:
    """Return the GCP project ID. Raises if not set."""
    project = get_settings().gcp_project_id
    if not project:
        raise AuthenticationError(
            "GCP_PROJECT_ID is not set. "
            "Also set GOOGLE_APPLICATION_CREDENTIALS or run `gcloud auth application-default login`."
        )
    log.debug("gcp_credentials_loaded", project=project)
    return project


def get_kubeconfig_path() -> str | None:
    """
    Return the path to the kubeconfig file, or None (uses in-cluster config).
    """
    path = get_settings().kubeconfig_path
    log.debug("kubeconfig_path_resolved", path=path or "in-cluster")
    return path
