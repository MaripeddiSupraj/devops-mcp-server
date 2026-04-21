"""tools/gcp/gcp_tools.py — GCP Compute, Storage, and GKE tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.gcp_client import GCPComputeClient, GCPStorageClient, GCPContainerClient

# ── gcp_list_instances ────────────────────────────────────────────────────────

INSTANCES_TOOL_NAME = "gcp_list_instances"
INSTANCES_TOOL_DESCRIPTION = (
    "Lists GCP Compute Engine instances. Optionally filter by zone. "
    "Shows name, zone, machine type, status, and internal IP. "
    "Requires GOOGLE_APPLICATION_CREDENTIALS or gcloud auth, and GCP_PROJECT_ID."
)
INSTANCES_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "zone": {
            "type": "string",
            "description": "GCP zone to filter by (e.g. 'us-central1-a'). Omit to list all zones.",
        },
    },
    "additionalProperties": False,
}


def instances_handler(zone: Optional[str] = None) -> List[Dict[str, Any]]:
    return GCPComputeClient().list_instances(zone=zone)


# ── gcp_list_buckets ──────────────────────────────────────────────────────────

BUCKETS_TOOL_NAME = "gcp_list_buckets"
BUCKETS_TOOL_DESCRIPTION = (
    "Lists all GCS (Google Cloud Storage) buckets in the project. "
    "Shows name, location, storage class, creation time, and versioning status."
)
BUCKETS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def buckets_handler() -> List[Dict[str, Any]]:
    return GCPStorageClient().list_buckets()


# ── gcp_list_gke_clusters ─────────────────────────────────────────────────────

GKE_TOOL_NAME = "gcp_list_gke_clusters"
GKE_TOOL_DESCRIPTION = (
    "Lists GKE (Google Kubernetes Engine) clusters in the project. "
    "Shows name, location, status, node count, Kubernetes version, and endpoint."
)
GKE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "zone": {
            "type": "string",
            "description": "Zone or region to filter clusters (default: '-' for all locations).",
            "default": "-",
        },
    },
    "additionalProperties": False,
}


def gke_handler(zone: str = "-") -> List[Dict[str, Any]]:
    return GCPContainerClient().list_clusters(zone=zone)


# ── gcp_cloudrun_list_services ────────────────────────────────────────────────

CLOUDRUN_TOOL_NAME = "gcp_cloudrun_list_services"
CLOUDRUN_TOOL_DESCRIPTION = (
    "Lists Google Cloud Run services, optionally filtered by region. "
    "Shows name, URL, region, and current condition status."
)
CLOUDRUN_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "region": {"type": "string", "description": "GCP region (e.g. 'us-central1'). Use '-' for all regions.", "default": "-"},
    },
    "additionalProperties": False,
}


def cloudrun_handler(region: str = "-") -> List[Dict[str, Any]]:
    from integrations.gcp_client import GCPCloudRunClient
    return GCPCloudRunClient().list_services(region=region)


# ── gcp_cloudsql_list_instances ───────────────────────────────────────────────

CLOUDSQL_TOOL_NAME = "gcp_cloudsql_list_instances"
CLOUDSQL_TOOL_DESCRIPTION = (
    "Lists Google Cloud SQL instances in the project. "
    "Shows name, database version, state, region, tier, and primary IP address."
)
CLOUDSQL_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def cloudsql_handler() -> List[Dict[str, Any]]:
    from integrations.gcp_client import GCPCloudSQLClient
    return GCPCloudSQLClient().list_instances()


# ── gcp_cloudbuild_list_builds ────────────────────────────────────────────────

CLOUDBUILD_LIST_TOOL_NAME = "gcp_cloudbuild_list_builds"
CLOUDBUILD_LIST_TOOL_DESCRIPTION = (
    "Lists recent Google Cloud Build executions. "
    "Shows build ID, status, source repo, branch, timestamps, and log URL."
)
CLOUDBUILD_LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "limit": {"type": "integer", "description": "Maximum builds to return (default: 20).", "default": 20},
    },
    "additionalProperties": False,
}


def cloudbuild_list_handler(limit: int = 20) -> List[Dict[str, Any]]:
    from integrations.gcp_client import GCPCloudBuildClient
    return GCPCloudBuildClient().list_builds(limit=limit)


# ── gcp_cloudbuild_trigger ────────────────────────────────────────────────────

CLOUDBUILD_TRIGGER_TOOL_NAME = "gcp_cloudbuild_trigger"
CLOUDBUILD_TRIGGER_TOOL_DESCRIPTION = (
    "Triggers a Cloud Build trigger by ID on a specified branch. "
    "Returns the build ID for status tracking."
)
CLOUDBUILD_TRIGGER_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "trigger_id": {"type": "string", "description": "Cloud Build trigger ID."},
        "branch": {"type": "string", "description": "Branch to build (default: main).", "default": "main"},
    },
    "required": ["trigger_id"],
    "additionalProperties": False,
}


def cloudbuild_trigger_handler(trigger_id: str, branch: str = "main") -> Dict[str, Any]:
    from integrations.gcp_client import GCPCloudBuildClient
    return GCPCloudBuildClient().trigger_build(trigger_id, branch)
