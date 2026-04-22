"""tools/docker/docker_tools.py — Docker image and container tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.docker_runner import DockerRunner

# ── docker_list_images ────────────────────────────────────────────────────────

LIST_IMAGES_TOOL_NAME = "docker_list_images"
LIST_IMAGES_TOOL_DESCRIPTION = "List locally available Docker images. Optionally filter by image name/tag."
LIST_IMAGES_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "filter": {"type": "string", "description": "Image name or tag to filter by (optional)."},
    },
    "additionalProperties": False,
}


def list_images_handler(filter: Optional[str] = None) -> List[Dict]:
    return DockerRunner().list_images(filter_ref=filter)


# ── docker_pull ───────────────────────────────────────────────────────────────

PULL_TOOL_NAME = "docker_pull"
PULL_TOOL_DESCRIPTION = "Pull a Docker image from a registry."
PULL_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "image": {"type": "string", "description": "Image name and tag (e.g. 'nginx:latest')."},
    },
    "required": ["image"],
    "additionalProperties": False,
}


def pull_handler(image: str) -> Dict:
    output = DockerRunner().pull(image)
    return {"image": image, "output": output}


# ── docker_build ──────────────────────────────────────────────────────────────

BUILD_TOOL_NAME = "docker_build"
BUILD_TOOL_DESCRIPTION = (
    "Build a Docker image from a Dockerfile. "
    "context is the build directory path. tag is the image name:tag to assign."
)
BUILD_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "context": {"type": "string", "description": "Path to the build context directory."},
        "tag": {"type": "string", "description": "Image tag (e.g. 'myapp:v1.2.3')."},
        "dockerfile": {"type": "string", "description": "Path to Dockerfile if not in context root (optional)."},
        "build_args": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "description": "Build-time variables as key/value pairs (optional).",
        },
    },
    "required": ["context", "tag"],
    "additionalProperties": False,
}


def build_handler(context: str, tag: str, dockerfile: Optional[str] = None, build_args: Optional[Dict[str, str]] = None) -> Dict:
    output = DockerRunner().build(context, tag, dockerfile=dockerfile, build_args=build_args)
    return {"tag": tag, "output": output}


# ── docker_push ───────────────────────────────────────────────────────────────

PUSH_TOOL_NAME = "docker_push"
PUSH_TOOL_DESCRIPTION = "Push a Docker image to a registry (Docker Hub, ECR, ACR, GCR, etc.)."
PUSH_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "image": {"type": "string", "description": "Fully qualified image name:tag to push."},
    },
    "required": ["image"],
    "additionalProperties": False,
}


def push_handler(image: str) -> Dict:
    output = DockerRunner().push(image)
    return {"image": image, "output": output}


# ── docker_inspect ────────────────────────────────────────────────────────────

INSPECT_TOOL_NAME = "docker_inspect"
INSPECT_TOOL_DESCRIPTION = "Inspect a Docker image — returns full metadata including layers, env, entrypoint, and labels."
INSPECT_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "image": {"type": "string", "description": "Image name or ID to inspect."},
    },
    "required": ["image"],
    "additionalProperties": False,
}


def inspect_handler(image: str) -> List[Dict]:
    return DockerRunner().inspect(image)


# ── docker_list_containers ────────────────────────────────────────────────────

LIST_CONTAINERS_TOOL_NAME = "docker_list_containers"
LIST_CONTAINERS_TOOL_DESCRIPTION = "List running Docker containers. Set all=true to include stopped containers."
LIST_CONTAINERS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "all": {"type": "boolean", "description": "Include stopped containers (default: false).", "default": False},
    },
    "additionalProperties": False,
}


def list_containers_handler(all: bool = False) -> List[Dict]:
    return DockerRunner().list_containers(all_containers=all)


# ── docker_logs ───────────────────────────────────────────────────────────────

LOGS_TOOL_NAME = "docker_logs"
LOGS_TOOL_DESCRIPTION = "Get the last N lines of logs from a running or stopped container."
LOGS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "container": {"type": "string", "description": "Container name or ID."},
        "tail": {"type": "integer", "description": "Number of log lines to return (default: 100).", "default": 100},
    },
    "required": ["container"],
    "additionalProperties": False,
}


def logs_handler(container: str, tail: int = 100) -> Dict:
    output = DockerRunner().logs(container, tail=tail)
    return {"container": container, "logs": output}


# ── docker_tag ────────────────────────────────────────────────────────────────

TAG_TOOL_NAME = "docker_tag"
TAG_TOOL_DESCRIPTION = "Tag an existing Docker image with a new name/tag (e.g. before pushing to a different registry)."
TAG_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "source": {"type": "string", "description": "Source image name:tag."},
        "target": {"type": "string", "description": "Target image name:tag."},
    },
    "required": ["source", "target"],
    "additionalProperties": False,
}


def tag_handler(source: str, target: str) -> Dict:
    DockerRunner().tag(source, target)
    return {"source": source, "target": target, "status": "tagged"}
