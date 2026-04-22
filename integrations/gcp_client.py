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


class GCPCloudRunClient:
    """GCP Cloud Run operations."""

    def __init__(self) -> None:
        from google.cloud import run_v2
        self._client = run_v2.ServicesClient()
        self._project = _project_id()

    def list_services(self, region: str = "-") -> List[Dict[str, Any]]:
        from google.cloud import run_v2
        try:
            parent = f"projects/{self._project}/locations/{region}"
            request = run_v2.ListServicesRequest(parent=parent)
            services = list(self._client.list_services(request=request))
        except Exception as exc:
            raise GCPClientError(f"list_services failed: {exc}") from exc
        return [
            {
                "name": s.name.split("/")[-1],
                "region": s.name.split("/")[3] if "/" in s.name else region,
                "url": s.uri,
                "condition": s.terminal_condition.state.name if s.terminal_condition else None,
                "last_modifier": s.last_modifier,
                "create_time": s.create_time.isoformat() if s.create_time else None,
            }
            for s in services
        ]


class GCPCloudSQLClient:
    """GCP Cloud SQL operations."""

    def __init__(self) -> None:
        import googleapiclient.discovery
        self._service = googleapiclient.discovery.build("sqladmin", "v1")
        self._project = _project_id()

    def list_instances(self) -> List[Dict[str, Any]]:
        try:
            resp = self._service.instances().list(project=self._project).execute()
        except Exception as exc:
            raise GCPClientError(f"list_instances failed: {exc}") from exc
        return [
            {
                "name": inst["name"],
                "database_version": inst.get("databaseVersion"),
                "state": inst.get("state"),
                "region": inst.get("region"),
                "tier": inst.get("settings", {}).get("tier"),
                "ip_address": next((ip["ipAddress"] for ip in inst.get("ipAddresses", []) if ip.get("type") == "PRIMARY"), None),
            }
            for inst in resp.get("items", [])
        ]


class GCPCloudBuildClient:
    """GCP Cloud Build operations."""

    def __init__(self) -> None:
        import googleapiclient.discovery
        self._service = googleapiclient.discovery.build("cloudbuild", "v1")
        self._project = _project_id()

    def list_builds(self, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            resp = self._service.projects().builds().list(projectId=self._project, pageSize=limit).execute()
        except Exception as exc:
            raise GCPClientError(f"list_builds failed: {exc}") from exc
        return [
            {
                "id": b["id"],
                "status": b.get("status"),
                "source": b.get("source", {}).get("repoSource", {}).get("repoName"),
                "branch": b.get("source", {}).get("repoSource", {}).get("branchName"),
                "create_time": b.get("createTime"),
                "finish_time": b.get("finishTime"),
                "log_url": b.get("logUrl"),
            }
            for b in resp.get("builds", [])
        ]

    def trigger_build(self, trigger_id: str, branch: str = "main") -> Dict[str, Any]:
        body = {"source": {"branchName": branch}}
        try:
            resp = self._service.projects().triggers().run(projectId=self._project, triggerId=trigger_id, body=body).execute()
        except Exception as exc:
            raise GCPClientError(f"trigger_build failed: {exc}") from exc
        log.info("gcp_build_triggered", trigger_id=trigger_id, branch=branch)
        return {"build_id": resp.get("name", "").split("/")[-1], "trigger_id": trigger_id, "branch": branch, "status": "QUEUED"}


class GCPSecretManagerClient:
    def __init__(self) -> None:
        self._project = _project_id()

    def get_secret(self, secret_id: str, version: str = "latest") -> Dict[str, Any]:
        from google.cloud import secretmanager
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self._project}/secrets/{secret_id}/versions/{version}"
            response = client.access_secret_version(request={"name": name})
        except Exception as exc:
            raise GCPClientError(f"get_secret failed: {exc}") from exc
        return {"secret_id": secret_id, "version": version, "value": response.payload.data.decode("utf-8")}

    def list_secrets(self) -> List[Dict[str, Any]]:
        from google.cloud import secretmanager
        try:
            client = secretmanager.SecretManagerServiceClient()
            secrets = list(client.list_secrets(request={"parent": f"projects/{self._project}"}))
        except Exception as exc:
            raise GCPClientError(f"list_secrets failed: {exc}") from exc
        return [{"name": s.name.split("/")[-1], "full_name": s.name} for s in secrets]

    def create_secret(self, secret_id: str, value: str) -> Dict[str, Any]:
        from google.cloud import secretmanager
        try:
            client = secretmanager.SecretManagerServiceClient()
            secret = client.create_secret(
                request={
                    "parent": f"projects/{self._project}",
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
            client.add_secret_version(request={"parent": secret.name, "payload": {"data": value.encode("utf-8")}})
        except Exception as exc:
            raise GCPClientError(f"create_secret failed: {exc}") from exc
        return {"secret_id": secret_id, "status": "created"}


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
