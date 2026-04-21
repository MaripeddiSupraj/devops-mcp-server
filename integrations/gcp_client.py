"""
integrations/gcp_client.py
---------------------------
Google Cloud SDK client factory.

Authentication is handled by Application Default Credentials (ADC):
  - Set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON key path, OR
  - Run `gcloud auth application-default login` for user credentials.

GCP_PROJECT_ID must be set in environment (or via settings).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

from core.auth import get_gcp_credentials
from core.logger import get_logger

log = get_logger(__name__)


class GCPClientError(RuntimeError):
    """Wraps Google Cloud SDK exceptions in a domain-specific error."""


@lru_cache(maxsize=1)
def _project_id() -> str:
    return get_gcp_credentials()


class GCPComputeClient:
    """GCP Compute Engine operations used by MCP tool handlers."""

    def __init__(self) -> None:
        from google.cloud import compute_v1
        self._instances = compute_v1.InstancesClient()
        self._zones = compute_v1.ZonesClient()
        self._project = _project_id()

    def list_instances(self, zone: Optional[str] = None) -> List[Dict[str, Any]]:
        from google.cloud import compute_v1
        try:
            if zone:
                request = compute_v1.ListInstancesRequest(project=self._project, zone=zone)
                instances = list(self._instances.list(request=request))
                raw = [(zone, i) for i in instances]
            else:
                agg_request = compute_v1.AggregatedListInstancesRequest(project=self._project)
                agg_list = self._instances.aggregated_list(request=agg_request)
                raw = []
                for z, scoped in agg_list:
                    for inst in (scoped.instances or []):
                        raw.append((z.replace("zones/", ""), inst))
        except Exception as exc:
            raise GCPClientError(f"list_instances failed: {exc}") from exc
        return [
            {
                "name": inst.name,
                "zone": z,
                "machine_type": inst.machine_type.split("/")[-1],
                "status": inst.status,
                "network_ip": inst.network_interfaces[0].network_i_p if inst.network_interfaces else None,
                "tags": list(inst.tags.items) if inst.tags else [],
            }
            for z, inst in raw
        ]


class GCPStorageClient:
    """GCP Cloud Storage operations used by MCP tool handlers."""

    def __init__(self) -> None:
        from google.cloud import storage
        self._client = storage.Client(project=_project_id())

    def list_buckets(self) -> List[Dict[str, Any]]:
        try:
            buckets = list(self._client.list_buckets())
        except Exception as exc:
            raise GCPClientError(f"list_buckets failed: {exc}") from exc
        return [
            {
                "name": b.name,
                "location": b.location,
                "storage_class": b.storage_class,
                "created": b.time_created.isoformat() if b.time_created else None,
                "versioning": b.versioning_enabled,
            }
            for b in buckets
        ]


class GCPContainerClient:
    """GCP Kubernetes Engine (GKE) operations used by MCP tool handlers."""

    def __init__(self) -> None:
        from google.cloud import container_v1
        self._client = container_v1.ClusterManagerClient()
        self._project = _project_id()

    def list_clusters(self, zone: str = "-") -> List[Dict[str, Any]]:
        from google.cloud import container_v1
        try:
            request = container_v1.ListClustersRequest(parent=f"projects/{self._project}/locations/{zone}")
            resp = self._client.list_clusters(request=request)
        except Exception as exc:
            raise GCPClientError(f"list_clusters failed: {exc}") from exc
        return [
            {
                "name": c.name,
                "location": c.location,
                "status": container_v1.Cluster.Status(c.status).name,
                "node_count": c.current_node_count,
                "k8s_version": c.current_master_version,
                "endpoint": c.endpoint,
            }
            for c in resp.clusters
        ]
