"""tools/github/get_workflow_run.py — MCP tool for fetching GitHub Actions run status."""

from __future__ import annotations

from typing import Any, Dict

from integrations.github_client import GitHubClient

TOOL_NAME = "github_get_workflow_run"
TOOL_DESCRIPTION = (
    "Fetches the status and conclusion of a specific GitHub Actions workflow run by ID. "
    "Use after github_trigger_workflow to check if it completed successfully."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "repo": {"type": "string", "description": "Repository in owner/repo format."},
        "run_id": {"type": "integer", "description": "Workflow run ID (returned by the GitHub API or visible in the Actions URL)."},
    },
    "required": ["repo", "run_id"],
    "additionalProperties": False,
}


def handler(repo: str, run_id: int) -> Dict[str, Any]:
    return GitHubClient().get_workflow_run(repo, run_id)
