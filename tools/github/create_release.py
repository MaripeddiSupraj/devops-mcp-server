"""
tools/github/create_release.py
--------------------------------
MCP tool: create a GitHub release.
"""

from __future__ import annotations

from typing import Any, Dict

from integrations.github_client import GitHubClient

TOOL_NAME = "github_create_release"
TOOL_DESCRIPTION = (
    "Create a GitHub release with a tag, title, and release notes. "
    "Supports draft and pre-release flags. Requires GITHUB_TOKEN."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "repo": {
            "type": "string",
            "description": "Repository full name in owner/repo format.",
        },
        "tag_name": {
            "type": "string",
            "description": "Tag to create for this release (e.g. v1.2.3).",
        },
        "name": {
            "type": "string",
            "description": "Release title displayed on GitHub.",
        },
        "body": {
            "type": "string",
            "description": "Release notes in Markdown format (optional).",
            "default": "",
        },
        "draft": {
            "type": "boolean",
            "description": "Publish as draft (not publicly visible). Default false.",
            "default": False,
        },
        "prerelease": {
            "type": "boolean",
            "description": "Mark as pre-release. Default false.",
            "default": False,
        },
        "target_commitish": {
            "type": "string",
            "description": "Branch or commit SHA the tag is created from (default: main).",
            "default": "main",
        },
    },
    "required": ["repo", "tag_name", "name"],
    "additionalProperties": False,
}


def handler(
    repo: str,
    tag_name: str,
    name: str,
    body: str = "",
    draft: bool = False,
    prerelease: bool = False,
    target_commitish: str = "main",
) -> Dict[str, Any]:
    """Create a GitHub release."""
    return GitHubClient().create_release(
        repo_full_name=repo,
        tag_name=tag_name,
        name=name,
        body=body,
        draft=draft,
        prerelease=prerelease,
        target_commitish=target_commitish,
    )
