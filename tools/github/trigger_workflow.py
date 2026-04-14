"""
tools/github/trigger_workflow.py
---------------------------------
MCP tool: trigger a GitHub Actions workflow dispatch.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from integrations.github_client import GitHubClient

TOOL_NAME = "github_trigger_workflow"
TOOL_DESCRIPTION = (
    "Trigger a GitHub Actions workflow via workflow_dispatch event. "
    "Useful for kicking off CI/CD pipelines, deployment workflows, or "
    "scheduled tasks on demand. Requires GITHUB_TOKEN with workflow scope."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "repo": {
            "type": "string",
            "description": "Repository full name in owner/repo format.",
        },
        "workflow_id": {
            "type": "string",
            "description": "Workflow file name (e.g. ci.yml) or numeric workflow ID.",
        },
        "ref": {
            "type": "string",
            "description": "Branch or tag to run the workflow on (default: main).",
            "default": "main",
        },
        "inputs": {
            "type": "object",
            "description": "Optional workflow_dispatch input parameters as key-value pairs.",
        },
    },
    "required": ["repo", "workflow_id"],
    "additionalProperties": False,
}


def handler(
    repo: str,
    workflow_id: str,
    ref: str = "main",
    inputs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Trigger a GitHub Actions workflow dispatch."""
    return GitHubClient().trigger_workflow(
        repo_full_name=repo,
        workflow_id=workflow_id,
        ref=ref,
        inputs=inputs,
    )
