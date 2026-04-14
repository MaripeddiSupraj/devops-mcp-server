"""
tools/github/list_issues.py
----------------------------
MCP tool: list GitHub issues in a repository.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.github_client import GitHubClient

TOOL_NAME = "github_list_issues"
TOOL_DESCRIPTION = (
    "List issues in a GitHub repository. Returns issue number, title, state, "
    "URL, author, labels, creation date, and comment count. "
    "Filters out pull requests automatically. Requires GITHUB_TOKEN."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "repo": {
            "type": "string",
            "description": "Repository full name in owner/repo format (e.g. octocat/Hello-World).",
        },
        "state": {
            "type": "string",
            "description": "Issue state to filter by.",
            "enum": ["open", "closed", "all"],
            "default": "open",
        },
        "label": {
            "type": "string",
            "description": "Filter issues by label name (optional).",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of issues to return (default 30).",
            "default": 30,
            "minimum": 1,
            "maximum": 100,
        },
    },
    "required": ["repo"],
    "additionalProperties": False,
}


def handler(
    repo: str,
    state: str = "open",
    label: Optional[str] = None,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """Return a list of GitHub issues."""
    return GitHubClient().list_issues(
        repo_full_name=repo,
        state=state,
        label=label,
        limit=limit,
    )
