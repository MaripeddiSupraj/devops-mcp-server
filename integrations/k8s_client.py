"""
integrations/k8s_client.py
---------------------------
Kubernetes client wrapper using the official kubernetes-client/python library.
Supports both in-cluster (pod SA token) and local kubeconfig authentication.

Improvements over v1:
- Config loaded once at module level via _get_k8s_config(), not per-instantiation.
- All API calls carry _request_timeout to avoid hanging on unresponsive clusters.
- All list operations paginate automatically (handles clusters with 500+ objects).
- datetime.utcnow() replaced with timezone-aware datetime.now(UTC) (Python 3.12+).
"""

from __future__ import annotations

import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException

from core.auth import get_kubeconfig_path
from core.logger import get_logger

log = get_logger(__name__)

# Default timeout for every Kubernetes API call (seconds).
# Prevents tools from hanging when the cluster is degraded.
_K8S_REQUEST_TIMEOUT: int = 30

# Page size for paginated list operations.
_PAGE_LIMIT: int = 500


class K8sClientError(RuntimeError):
    """Wraps kubernetes SDK errors in a domain-specific error."""


# ── Config singleton ──────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_k8s_config() -> None:
    """
    Load kubeconfig exactly once for the lifetime of the process.

    Uses ``@lru_cache`` so that repeated KubernetesClient() instantiations
    in tool handlers do not reload the file on every call.
    """
    path = get_kubeconfig_path()
    try:
        if path:
            k8s_config.load_kube_config(config_file=path)
            log.info("k8s_kubeconfig_loaded", path=path)
        else:
            k8s_config.load_incluster_config()
            log.info("k8s_incluster_config_loaded")
    except k8s_config.ConfigException as exc:
        raise K8sClientError(f"Failed to load Kubernetes config: {exc}") from exc


# ── Pagination helper ─────────────────────────────────────────────────────────

def _paginate(list_fn, **kwargs) -> list:
    """
    Exhaust a Kubernetes list API that may return paginated results.

    Args:
        list_fn:  Bound method such as ``core_v1.list_namespaced_pod``.
        **kwargs: Parameters forwarded to every page call (namespace, selectors, etc.).
                  ``limit`` and ``_continue`` are managed internally.

    Returns:
        Flat list of all items across all pages.
    """
    kwargs.setdefault("_request_timeout", _K8S_REQUEST_TIMEOUT)
    kwargs["limit"] = _PAGE_LIMIT
    items: list = []
    continue_token: Optional[str] = None

    while True:
        if continue_token:
            kwargs["_continue"] = continue_token
        resp = list_fn(**kwargs)
        items.extend(resp.items)
        continue_token = (resp.metadata or {}) and getattr(resp.metadata, "_continue", None)
        if not continue_token:
            break

    return items


# ── Client class ──────────────────────────────────────────────────────────────

class KubernetesClient:
    """High-level Kubernetes operations for MCP tool handlers."""

    def __init__(self) -> None:
        _get_k8s_config()          # no-op after first call — cached
        self._core = k8s_client.CoreV1Api()
        self._apps = k8s_client.AppsV1Api()

    # ── Pods ──────────────────────────────────────────────────────────────────

    def get_pods(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """
        List all pods in *namespace* (paginated).

        Returns:
            List of dicts with ``name``, ``status``, ``ready``, ``restarts``, ``node``, ``ip``.
        """
        try:
            pod_items = _paginate(self._core.list_namespaced_pod, namespace=namespace)
        except ApiException as exc:
            raise K8sClientError(f"list_namespaced_pod failed: {exc}") from exc

        pods = []
        for pod in pod_items:
            container_statuses = pod.status.container_statuses or []
            # all() on empty list returns True — only mark ready when at least one container
            ready = bool(container_statuses) and all(cs.ready for cs in container_statuses)
            restarts = sum(cs.restart_count for cs in container_statuses)
            pods.append(
                {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "status": pod.status.phase,
                    "ready": ready,
                    "restarts": restarts,
                    "node": pod.spec.node_name,
                    "ip": pod.status.pod_ip,
                }
            )
        return pods

    # ── Deployments ───────────────────────────────────────────────────────────

    def deploy(
        self,
        name: str,
        image: str,
        namespace: str = "default",
        replicas: int = 1,
        port: int = 80,
        labels: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create or update a Deployment."""
        base_labels = {"app": name}
        if labels:
            base_labels.update(labels)

        deployment = k8s_client.V1Deployment(
            metadata=k8s_client.V1ObjectMeta(name=name, labels=base_labels),
            spec=k8s_client.V1DeploymentSpec(
                replicas=replicas,
                selector=k8s_client.V1LabelSelector(match_labels={"app": name}),
                template=k8s_client.V1PodTemplateSpec(
                    metadata=k8s_client.V1ObjectMeta(labels={"app": name}),
                    spec=k8s_client.V1PodSpec(
                        containers=[
                            k8s_client.V1Container(
                                name=name,
                                image=image,
                                ports=[k8s_client.V1ContainerPort(container_port=port)],
                            )
                        ]
                    ),
                ),
            ),
        )

        try:
            self._apps.read_namespaced_deployment(
                name=name, namespace=namespace, _request_timeout=_K8S_REQUEST_TIMEOUT
            )
            result = self._apps.patch_namespaced_deployment(
                name=name, namespace=namespace, body=deployment,
                _request_timeout=_K8S_REQUEST_TIMEOUT,
            )
            action = "updated"
        except ApiException as exc:
            if exc.status == 404:
                result = self._apps.create_namespaced_deployment(
                    namespace=namespace, body=deployment,
                    _request_timeout=_K8S_REQUEST_TIMEOUT,
                )
                action = "created"
            else:
                raise K8sClientError(f"deploy failed: {exc}") from exc

        log.info("k8s_deployment_applied", name=name, namespace=namespace, image=image, action=action)
        return {
            "name": result.metadata.name,
            "namespace": result.metadata.namespace,
            "replicas": result.spec.replicas,
            "image": image,
            "action": action,
        }

    def get_deployments(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """List deployments in *namespace* (paginated)."""
        try:
            items = _paginate(self._apps.list_namespaced_deployment, namespace=namespace)
        except ApiException as exc:
            raise K8sClientError(f"list_namespaced_deployment failed: {exc}") from exc

        return [
            {
                "name": d.metadata.name,
                "namespace": d.metadata.namespace,
                "replicas": d.spec.replicas,
                "available": d.status.available_replicas or 0,
                "ready": d.status.ready_replicas or 0,
                "image": d.spec.template.spec.containers[0].image
                if d.spec.template.spec.containers else None,
                "conditions": [
                    {"type": c.type, "status": c.status, "reason": c.reason}
                    for c in (d.status.conditions or [])
                ],
            }
            for d in items
        ]

    # ── Logs ──────────────────────────────────────────────────────────────────

    def get_logs(
        self,
        pod_name: str,
        namespace: str = "default",
        container: Optional[str] = None,
        tail_lines: int = 100,
        previous: bool = False,
    ) -> Dict[str, Any]:
        """Fetch logs from a pod container."""
        kwargs: Dict[str, Any] = {
            "name": pod_name,
            "namespace": namespace,
            "tail_lines": tail_lines,
            "previous": previous,
            "_preload_content": True,
            "_request_timeout": _K8S_REQUEST_TIMEOUT,
        }
        if container:
            kwargs["container"] = container

        try:
            log_text: str = self._core.read_namespaced_pod_log(**kwargs)
        except ApiException as exc:
            raise K8sClientError(f"read_namespaced_pod_log failed: {exc}") from exc

        lines = log_text.splitlines()
        log.info("k8s_logs_fetched", pod=pod_name, namespace=namespace, lines=len(lines))
        return {
            "pod": pod_name,
            "namespace": namespace,
            "container": container or "auto",
            "tail_lines": tail_lines,
            "previous": previous,
            "lines": len(lines),
            "log": log_text,
        }

    # ── Events ────────────────────────────────────────────────────────────────

    def get_events(
        self,
        namespace: str = "default",
        field_selector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return Kubernetes events for *namespace*, paginated, warnings first."""
        kwargs: Dict[str, Any] = {"namespace": namespace}
        if field_selector:
            kwargs["field_selector"] = field_selector

        try:
            event_items = _paginate(self._core.list_namespaced_event, **kwargs)
        except ApiException as exc:
            raise K8sClientError(f"list_namespaced_event failed: {exc}") from exc

        events = [
            {
                "type": e.type,
                "reason": e.reason,
                "message": e.message,
                "object": f"{e.involved_object.kind}/{e.involved_object.name}",
                "count": e.count or 1,
                "first_time": str(e.first_timestamp) if e.first_timestamp else None,
                "last_time": str(e.last_timestamp) if e.last_timestamp else None,
            }
            for e in event_items
        ]
        events.sort(key=lambda x: (x["type"] != "Warning", x["last_time"] or ""), reverse=False)
        return events

    # ── Scale ─────────────────────────────────────────────────────────────────

    def scale_deployment(self, name: str, replicas: int, namespace: str = "default") -> Dict[str, Any]:
        """Patch the replica count of a Deployment."""
        try:
            current = self._apps.read_namespaced_deployment(
                name=name, namespace=namespace, _request_timeout=_K8S_REQUEST_TIMEOUT
            )
        except ApiException as exc:
            raise K8sClientError(f"Deployment '{name}' not found: {exc}") from exc

        previous = current.spec.replicas
        try:
            result = self._apps.patch_namespaced_deployment(
                name=name, namespace=namespace, body={"spec": {"replicas": replicas}},
                _request_timeout=_K8S_REQUEST_TIMEOUT,
            )
        except ApiException as exc:
            raise K8sClientError(f"scale_deployment failed: {exc}") from exc

        log.info("k8s_deployment_scaled", name=name, namespace=namespace, previous=previous, new=replicas)
        return {
            "name": name,
            "namespace": namespace,
            "previous_replicas": previous,
            "new_replicas": result.spec.replicas,
        }

    # ── Rollout ───────────────────────────────────────────────────────────────

    def rollout_restart(self, name: str, namespace: str = "default") -> Dict[str, Any]:
        """Trigger a rolling restart by patching the restartedAt annotation."""
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {"kubectl.kubernetes.io/restartedAt": now}
                    }
                }
            }
        }
        try:
            self._apps.patch_namespaced_deployment(
                name=name, namespace=namespace, body=body,
                _request_timeout=_K8S_REQUEST_TIMEOUT,
            )
        except ApiException as exc:
            raise K8sClientError(f"rollout_restart failed for '{name}': {exc}") from exc

        log.info("k8s_rollout_restart_triggered", name=name, namespace=namespace)
        return {
            "name": name,
            "namespace": namespace,
            "action": "rollout_restart",
            "triggered_at": now,
            "message": f"Rolling restart triggered for deployment '{name}'.",
        }

    def rollout_status(self, name: str, namespace: str = "default") -> Dict[str, Any]:
        """Return current rollout progress for a Deployment."""
        try:
            d = self._apps.read_namespaced_deployment(
                name=name, namespace=namespace, _request_timeout=_K8S_REQUEST_TIMEOUT
            )
        except ApiException as exc:
            raise K8sClientError(f"Deployment '{name}' not found: {exc}") from exc

        desired = d.spec.replicas or 0
        updated = d.status.updated_replicas or 0
        ready = d.status.ready_replicas or 0
        available = d.status.available_replicas or 0
        complete = (updated == desired) and (ready == desired) and (available == desired)

        return {
            "name": name,
            "namespace": namespace,
            "desired": desired,
            "updated": updated,
            "ready": ready,
            "available": available,
            "complete": complete,
            "conditions": [
                {"type": c.type, "status": c.status, "message": c.message}
                for c in (d.status.conditions or [])
            ],
        }

    # ── Services ──────────────────────────────────────────────────────────────

    def get_services(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """List services in *namespace* (paginated)."""
        try:
            svc_items = _paginate(self._core.list_namespaced_service, namespace=namespace)
        except ApiException as exc:
            raise K8sClientError(f"list_namespaced_service failed: {exc}") from exc

        services = []
        for svc in svc_items:
            ports = [
                {
                    "port": p.port,
                    "target_port": str(p.target_port),
                    "protocol": p.protocol,
                    "node_port": p.node_port,
                }
                for p in (svc.spec.ports or [])
            ]
            lb = svc.status.load_balancer
            external_ip = (
                lb.ingress[0].ip
                if lb and lb.ingress
                else svc.spec.external_i_ps or None
            )
            services.append(
                {
                    "name": svc.metadata.name,
                    "namespace": svc.metadata.namespace,
                    "type": svc.spec.type,
                    "cluster_ip": svc.spec.cluster_ip,
                    "external_ip": external_ip,
                    "ports": ports,
                    "selector": svc.spec.selector or {},
                }
            )
        return services

    # ── Nodes ─────────────────────────────────────────────────────────────────

    def get_nodes(self) -> List[Dict[str, Any]]:
        """Return health and capacity for all cluster nodes (paginated)."""
        try:
            node_items = _paginate(self._core.list_node)
        except ApiException as exc:
            raise K8sClientError(f"list_node failed: {exc}") from exc

        nodes = []
        for node in node_items:
            labels = node.metadata.labels or {}
            roles = [
                lbl.split("/")[-1]
                for lbl in labels
                if lbl.startswith("node-role.kubernetes.io/")
            ] or ["worker"]
            conditions = {c.type: c.status for c in (node.status.conditions or [])}
            capacity = node.status.capacity or {}
            nodes.append(
                {
                    "name": node.metadata.name,
                    "ready": conditions.get("Ready") == "True",
                    "roles": roles,
                    "k8s_version": node.status.node_info.kubelet_version,
                    "os": node.status.node_info.os_image,
                    "container_runtime": node.status.node_info.container_runtime_version,
                    "cpu": capacity.get("cpu"),
                    "memory": capacity.get("memory"),
                    "conditions": [
                        {"type": c.type, "status": c.status}
                        for c in (node.status.conditions or [])
                    ],
                }
            )
        return nodes

    # ── Delete Pod ────────────────────────────────────────────────────────────

    def delete_pod(
        self,
        pod_name: str,
        namespace: str = "default",
        grace_period_seconds: int = 30,
    ) -> Dict[str, Any]:
        """Delete a pod; Kubernetes recreates it via the owning controller."""
        try:
            self._core.delete_namespaced_pod(
                name=pod_name,
                namespace=namespace,
                grace_period_seconds=grace_period_seconds,
                _request_timeout=_K8S_REQUEST_TIMEOUT,
            )
        except ApiException as exc:
            if exc.status == 404:
                raise K8sClientError(
                    f"Pod '{pod_name}' not found in namespace '{namespace}'."
                ) from exc
            raise K8sClientError(f"delete_namespaced_pod failed: {exc}") from exc

        log.info("k8s_pod_deleted", pod=pod_name, namespace=namespace, grace_period=grace_period_seconds)
        return {
            "pod": pod_name,
            "namespace": namespace,
            "action": "deleted",
            "grace_period_seconds": grace_period_seconds,
            "message": (
                f"Pod '{pod_name}' deleted. "
                "Kubernetes will reschedule it if managed by a controller."
            ),
        }
