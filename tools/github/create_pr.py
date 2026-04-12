"""
tools/github/create_pr.py
--------------------------
MCP tool definition for ``github_create_pull_request``.
"""

from __future__ import annotations

from typing import Any, Dict

from integrations.github_client import GitHubClient

TOOL_NAME = "github_create_pull_request"
TOOL_DESCRIPTION = (
    "Opens a new pull request on GitHub. "
    "Requires GITHUB_TOKEN environment variable with repo write access."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "repo": {
            "type": "string",
            "description": "Full repository name in 'owner/repo' format.",
        },
        "title": {
            "type": "string",
            "description": "Pull request title.",
        },
        "body": {
            "type": "string",
            "description": "Pull request description (Markdown supported).",
        },
        "head": {
            "type": "string",
            "description": "Name of the source branch to merge from.",
        },
        "base": {
            "type": "string",
            "description": "Name of the target branch to merge into.",
            "default": "main",
        },
        "draft": {
            "type": "boolean",
            "description": "Create as a draft pull request.",
            "default": False,
        },
    },
    "required": ["repo", "title", "body", "head"],
    "additionalProperties": False,
}


def handler(
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str = "main",
    draft: bool = False,
) -> Dict[str, Any]:
    """
    Create a GitHub pull request.

    Returns:
        Dict with ``number``, ``url``, ``state``, ``title``.
    """
    gh = GitHubClient()
    return gh.create_pull_request(
        repo_full_name=repo,
        title=title,
        body=body,
        head=head,
        base=base,
        draft=draft,
    )
