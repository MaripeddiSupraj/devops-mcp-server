"""
tools/github/get_repo.py
-------------------------
MCP tool definition for ``github_get_repo``.
"""

from __future__ import annotations

from typing import Any, Dict

from integrations.github_client import GitHubClient

TOOL_NAME = "github_get_repo"
TOOL_DESCRIPTION = (
    "Fetches metadata for a GitHub repository including stars, forks, "
    "open issues, default branch, and language."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "repo": {
            "type": "string",
            "description": "Full repository name in 'owner/repo' format.",
        }
    },
    "required": ["repo"],
    "additionalProperties": False,
}


def handler(repo: str) -> Dict[str, Any]:
    """
    Retrieve GitHub repository information.

    Args:
        repo: ``owner/repo`` string.

    Returns:
        Dict with repo metadata.
    """
    gh = GitHubClient()
    return gh.get_repo_info(repo)
