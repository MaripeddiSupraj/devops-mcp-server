"""tools/gitlab/gitlab_tools.py — GitLab SCM and CI/CD tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.gitlab_client import GitLabClient

# ── gitlab_list_projects ──────────────────────────────────────────────────────

LIST_PROJECTS_TOOL_NAME = "gitlab_list_projects"
LIST_PROJECTS_TOOL_DESCRIPTION = (
    "List GitLab projects accessible to the token, optionally filtered by name search. "
    "Requires GITLAB_TOKEN and GITLAB_URL."
)
LIST_PROJECTS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "search": {"type": "string", "description": "Search term to filter projects by name (optional)."},
        "limit": {"type": "integer", "description": "Max projects to return (default: 20).", "default": 20},
    },
    "additionalProperties": False,
}


def list_projects_handler(search: Optional[str] = None, limit: int = 20) -> List[Dict]:
    return GitLabClient().list_projects(search=search, limit=limit)


# ── gitlab_list_merge_requests ────────────────────────────────────────────────

LIST_MRS_TOOL_NAME = "gitlab_list_merge_requests"
LIST_MRS_TOOL_DESCRIPTION = "List merge requests for a GitLab project. Filter by state (opened, merged, closed)."
LIST_MRS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "project_id": {"type": "string", "description": "GitLab project ID or URL-encoded path (e.g. 'group/repo')."},
        "state": {"type": "string", "enum": ["opened", "merged", "closed", "all"], "default": "opened"},
    },
    "required": ["project_id"],
    "additionalProperties": False,
}


def list_mrs_handler(project_id: str, state: str = "opened") -> List[Dict]:
    return GitLabClient().list_merge_requests(project_id, state=state)


# ── gitlab_create_merge_request ───────────────────────────────────────────────

CREATE_MR_TOOL_NAME = "gitlab_create_merge_request"
CREATE_MR_TOOL_DESCRIPTION = "Create a merge request in a GitLab project."
CREATE_MR_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "project_id": {"type": "string", "description": "GitLab project ID or URL-encoded path."},
        "title": {"type": "string", "description": "MR title."},
        "source_branch": {"type": "string", "description": "Source branch name."},
        "target_branch": {"type": "string", "description": "Target branch name."},
        "description": {"type": "string", "description": "MR description (optional).", "default": ""},
    },
    "required": ["project_id", "title", "source_branch", "target_branch"],
    "additionalProperties": False,
}


def create_mr_handler(project_id: str, title: str, source_branch: str, target_branch: str, description: str = "") -> Dict:
    return GitLabClient().create_merge_request(project_id, title, source_branch, target_branch, description=description)


# ── gitlab_merge_mr ───────────────────────────────────────────────────────────

MERGE_MR_TOOL_NAME = "gitlab_merge_mr"
MERGE_MR_TOOL_DESCRIPTION = "Merge an open GitLab merge request by its IID."
MERGE_MR_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "project_id": {"type": "string", "description": "GitLab project ID or path."},
        "mr_iid": {"type": "integer", "description": "Merge request IID (internal project ID)."},
    },
    "required": ["project_id", "mr_iid"],
    "additionalProperties": False,
}


def merge_mr_handler(project_id: str, mr_iid: int) -> Dict:
    return GitLabClient().merge_mr(project_id, mr_iid)


# ── gitlab_list_pipelines ─────────────────────────────────────────────────────

LIST_PIPELINES_TOOL_NAME = "gitlab_list_pipelines"
LIST_PIPELINES_TOOL_DESCRIPTION = "List CI/CD pipelines for a GitLab project. Optionally filter by status."
LIST_PIPELINES_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "project_id": {"type": "string", "description": "GitLab project ID or path."},
        "status": {
            "type": "string",
            "enum": ["created", "waiting_for_resource", "preparing", "pending", "running", "success", "failed", "canceled", "skipped"],
            "description": "Filter by pipeline status (optional).",
        },
    },
    "required": ["project_id"],
    "additionalProperties": False,
}


def list_pipelines_handler(project_id: str, status: Optional[str] = None) -> List[Dict]:
    return GitLabClient().list_pipelines(project_id, status=status)


# ── gitlab_trigger_pipeline ───────────────────────────────────────────────────

TRIGGER_PIPELINE_TOOL_NAME = "gitlab_trigger_pipeline"
TRIGGER_PIPELINE_TOOL_DESCRIPTION = "Trigger a new CI/CD pipeline for a GitLab project on a given ref (branch or tag)."
TRIGGER_PIPELINE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "project_id": {"type": "string", "description": "GitLab project ID or path."},
        "ref": {"type": "string", "description": "Branch or tag name to run the pipeline on."},
    },
    "required": ["project_id", "ref"],
    "additionalProperties": False,
}


def trigger_pipeline_handler(project_id: str, ref: str) -> Dict:
    return GitLabClient().trigger_pipeline(project_id, ref)


# ── gitlab_list_issues ────────────────────────────────────────────────────────

LIST_ISSUES_TOOL_NAME = "gitlab_list_issues"
LIST_ISSUES_TOOL_DESCRIPTION = "List issues for a GitLab project. Optionally filter by state."
LIST_ISSUES_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "project_id": {"type": "string", "description": "GitLab project ID or path."},
        "state": {"type": "string", "enum": ["opened", "closed", "all"], "default": "opened"},
    },
    "required": ["project_id"],
    "additionalProperties": False,
}


def list_issues_handler(project_id: str, state: str = "opened") -> List[Dict]:
    return GitLabClient().list_issues(project_id, state=state)
