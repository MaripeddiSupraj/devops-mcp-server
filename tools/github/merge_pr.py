"""tools/github/merge_pr.py — MCP tool for merging GitHub pull requests."""

from __future__ import annotations

from typing import Any, Dict

from integrations.github_client import GitHubClient

TOOL_NAME = "github_merge_pr"
TOOL_DESCRIPTION = (
    "Merges an open pull request. Supports merge, squash, and rebase strategies. "
    "The PR must be mergeable (no conflicts, required checks passing)."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "repo": {"type": "string", "description": "Repository in owner/repo format."},
        "pr_number": {"type": "integer", "description": "Pull request number."},
        "merge_method": {
            "type": "string",
            "description": "Merge strategy.",
            "enum": ["merge", "squash", "rebase"],
            "default": "merge",
        },
        "commit_message": {
            "type": "string",
            "description": "Optional commit message override (defaults to PR title).",
            "default": "",
        },
    },
    "required": ["repo", "pr_number"],
    "additionalProperties": False,
}


def handler(repo: str, pr_number: int, merge_method: str = "merge", commit_message: str = "") -> Dict[str, Any]:
    return GitHubClient().merge_pr(repo, pr_number, merge_method, commit_message)
