"""tools/github/create_issue.py — MCP tool for creating GitHub issues."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.github_client import GitHubClient

TOOL_NAME = "github_create_issue"
TOOL_DESCRIPTION = (
    "Creates a new GitHub issue in the specified repository. "
    "Supports labels and assignees."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "repo": {"type": "string", "description": "Repository in owner/repo format."},
        "title": {"type": "string", "description": "Issue title."},
        "body": {"type": "string", "description": "Issue description (Markdown supported).", "default": ""},
        "labels": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Label names to apply (must already exist in the repo).",
        },
        "assignees": {
            "type": "array",
            "items": {"type": "string"},
            "description": "GitHub usernames to assign.",
        },
    },
    "required": ["repo", "title"],
    "additionalProperties": False,
}


def handler(
    repo: str,
    title: str,
    body: str = "",
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return GitHubClient().create_issue(repo, title, body, labels, assignees)
