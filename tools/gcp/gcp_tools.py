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
