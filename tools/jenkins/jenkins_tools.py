"""tools/jenkins/jenkins_tools.py — Jenkins CI/CD tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.jenkins_client import JenkinsClient

# ── jenkins_list_jobs ─────────────────────────────────────────────────────────

LIST_JOBS_TOOL_NAME = "jenkins_list_jobs"
LIST_JOBS_TOOL_DESCRIPTION = (
    "List all Jenkins jobs with their current status (blue=passing, red=failing, grey=disabled). "
    "Requires JENKINS_URL, JENKINS_USER, JENKINS_TOKEN."
)
LIST_JOBS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def list_jobs_handler() -> List[Dict]:
    return JenkinsClient().list_jobs()


# ── jenkins_get_job ───────────────────────────────────────────────────────────

GET_JOB_TOOL_NAME = "jenkins_get_job"
GET_JOB_TOOL_DESCRIPTION = "Get details for a Jenkins job including last build, last successful, and last failed build."
GET_JOB_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "job_name": {"type": "string", "description": "Jenkins job name."},
    },
    "required": ["job_name"],
    "additionalProperties": False,
}


def get_job_handler(job_name: str) -> Dict:
    return JenkinsClient().get_job(job_name)


# ── jenkins_trigger_build ─────────────────────────────────────────────────────

TRIGGER_BUILD_TOOL_NAME = "jenkins_trigger_build"
TRIGGER_BUILD_TOOL_DESCRIPTION = (
    "Trigger a Jenkins build for a job. "
    "Pass params as key/value pairs for parameterised builds."
)
TRIGGER_BUILD_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "job_name": {"type": "string", "description": "Jenkins job name."},
        "params": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "description": "Build parameters as key/value pairs (optional).",
        },
    },
    "required": ["job_name"],
    "additionalProperties": False,
}


def trigger_build_handler(job_name: str, params: Optional[Dict[str, str]] = None) -> Dict:
    return JenkinsClient().trigger_build(job_name, params=params)


# ── jenkins_get_build ─────────────────────────────────────────────────────────

GET_BUILD_TOOL_NAME = "jenkins_get_build"
GET_BUILD_TOOL_DESCRIPTION = "Get the status and result of a specific Jenkins build number."
GET_BUILD_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "job_name": {"type": "string", "description": "Jenkins job name."},
        "build_number": {"type": "integer", "description": "Build number to retrieve."},
    },
    "required": ["job_name", "build_number"],
    "additionalProperties": False,
}


def get_build_handler(job_name: str, build_number: int) -> Dict:
    return JenkinsClient().get_build(job_name, build_number)


# ── jenkins_get_build_log ─────────────────────────────────────────────────────

GET_BUILD_LOG_TOOL_NAME = "jenkins_get_build_log"
GET_BUILD_LOG_TOOL_DESCRIPTION = "Retrieve the console log output for a Jenkins build."
GET_BUILD_LOG_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "job_name": {"type": "string", "description": "Jenkins job name."},
        "build_number": {"type": "integer", "description": "Build number."},
    },
    "required": ["job_name", "build_number"],
    "additionalProperties": False,
}


def get_build_log_handler(job_name: str, build_number: int) -> Dict:
    log = JenkinsClient().get_build_log(job_name, build_number)
    return {"job": job_name, "build_number": build_number, "log": log}


# ── jenkins_list_builds ───────────────────────────────────────────────────────

LIST_BUILDS_TOOL_NAME = "jenkins_list_builds"
LIST_BUILDS_TOOL_DESCRIPTION = "List recent builds for a Jenkins job with their result and duration."
LIST_BUILDS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "job_name": {"type": "string", "description": "Jenkins job name."},
        "limit": {"type": "integer", "description": "Number of builds to return (default: 10).", "default": 10},
    },
    "required": ["job_name"],
    "additionalProperties": False,
}


def list_builds_handler(job_name: str, limit: int = 10) -> List[Dict]:
    return JenkinsClient().list_builds(job_name, limit=limit)
