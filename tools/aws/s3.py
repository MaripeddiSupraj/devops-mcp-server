"""
tools/aws/s3.py
---------------
MCP tool definitions for S3 operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.aws_client import S3Client

# ── list_s3_buckets ──────────────────────────────────────────────────────────

LIST_TOOL_NAME = "aws_list_s3_buckets"
LIST_TOOL_DESCRIPTION = "Lists all S3 buckets owned by the authenticated AWS account."
LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def list_handler() -> List[Dict[str, Any]]:
    """Return all S3 buckets for the current AWS account."""
    return S3Client().list_buckets()


# ── create_s3_bucket ─────────────────────────────────────────────────────────

TOOL_NAME = "aws_create_s3_bucket"
TOOL_DESCRIPTION = (
    "Creates a new S3 bucket with public access blocked by default. "
    "Bucket names must be globally unique."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "bucket_name": {
            "type": "string",
            "description": "Globally unique bucket name (3-63 lowercase chars).",
            "minLength": 3,
            "maxLength": 63,
            "pattern": "^[a-z0-9][a-z0-9\\-]*[a-z0-9]$",
        },
        "region": {
            "type": "string",
            "description": "AWS region (defaults to AWS_REGION env var).",
        },
    },
    "required": ["bucket_name"],
    "additionalProperties": False,
}


def handler(bucket_name: str, region: Optional[str] = None) -> Dict[str, Any]:
    """
    Create an S3 bucket with all public access blocked.

    Returns:
        Dict with ``bucket``, ``region``, ``public_access``.
    """
    return S3Client().create_bucket(bucket_name=bucket_name, region=region)
