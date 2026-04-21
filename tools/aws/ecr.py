"""tools/aws/ecr.py — AWS Elastic Container Registry tools."""

from __future__ import annotations

from typing import Any, Dict, List

from integrations.aws_client import ECRClient

# ── aws_ecr_list_repos ────────────────────────────────────────────────────────

LIST_REPOS_TOOL_NAME = "aws_ecr_list_repos"
LIST_REPOS_TOOL_DESCRIPTION = (
    "Lists all ECR (Elastic Container Registry) repositories in the current region. "
    "Shows name, URI, ARN, creation date, and scan-on-push setting."
)
LIST_REPOS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def list_repos_handler() -> List[Dict[str, Any]]:
    return ECRClient().list_repositories()


# ── aws_ecr_list_images ───────────────────────────────────────────────────────

LIST_IMAGES_TOOL_NAME = "aws_ecr_list_images"
LIST_IMAGES_TOOL_DESCRIPTION = (
    "Lists images in an ECR repository. "
    "Shows image digest, tags, push date, size, and vulnerability scan status."
)
LIST_IMAGES_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "repository_name": {"type": "string", "description": "ECR repository name."},
        "max_results": {"type": "integer", "description": "Maximum images to return (default: 50).", "default": 50},
    },
    "required": ["repository_name"],
    "additionalProperties": False,
}


def list_images_handler(repository_name: str, max_results: int = 50) -> List[Dict[str, Any]]:
    return ECRClient().list_images(repository_name, max_results)
