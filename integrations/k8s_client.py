"""
integrations/k8s_client.py
---------------------------
Kubernetes client wrapper using the official kubernetes-client/python library.
Supports both in-cluster (pod SA token) and local kubeconfig authentication.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException

from core.auth import get_kubeconfig_path
from core.logger import get_logger

log = get_logger(__name__)


class K8sClientError(RuntimeError):
    """Wraps kubernetes SDK errors in a domain-specific error."""


def _load_kube_config() -> None:
    """Load kubeconfig from file or in-cluster service account."""
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


class KubernetesClient:
    """
    High-level Kubernetes operations for MCP tool handlers.
    """

    def __init__(self) -> None:
        _load_kube_config()
        self._core = k8s_client.CoreV1Api()
        self._apps = k8s_client.AppsV1Api()

    # ── Pods ──────────────────────────────────────────────────────────────────

    def get_pods(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """
        List all pods in *namespace*.

        Returns:
            List of dicts with ``name``, ``status``, ``ready``, ``restarts``, ``node``.
        """
        try:
            resp = self._core.list_namespaced_pod(namespace=namespace)
        except ApiException as exc:
            raise K8sClientError(f"list_namespaced_pod failed: {exc}") from exc

        pods = []
        for pod in resp.items:
            container_statuses = pod.status.container_statuses or []
            ready = all(cs.ready for cs in container_statuses)
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
        """
        Create or replace a Deployment.

        Args:
            name:      Deployment name.
            image:     Container image (e.g. ``nginx:1.25``).
            namespace: Target namespace.
            replicas:  Desired replica count.
            port:      Container port.
            labels:    Extra labels to apply.

        Returns:
            Dict with deployment metadata.
        """
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
            existing = self._apps.read_namespaced_deployment(name=name, namespace=namespace)
            # Deployment exists → patch it
            result = self._apps.patch_namespaced_deployment(
                name=name, namespace=namespace, body=deployment
            )
            action = "updated"
        except ApiException as exc:
            if exc.status == 404:
                result = self._apps.create_namespaced_deployment(
                    namespace=namespace, body=deployment
                )
                action = "created"
            else:
                raise K8sClientError(f"deploy failed: {exc}") from exc

        log.info(
            "k8s_deployment_applied",
            name=name,
            namespace=namespace,
            image=image,
            action=action,
        )
        return {
            "name": result.metadata.name,
            "namespace": result.metadata.namespace,
            "replicas": result.spec.replicas,
            "image": image,
            "action": action,
        }

    def get_deployments(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """List deployments in *namespace*."""
        try:
            resp = self._apps.list_namespaced_deployment(namespace=namespace)
        except ApiException as exc:
            raise K8sClientError(f"list_namespaced_deployment failed: {exc}") from exc

        return [
            {
                "name": d.metadata.name,
                "namespace": d.metadata.namespace,
                "replicas": d.spec.replicas,
                "available": d.status.available_replicas or 0,
                "ready": d.status.ready_replicas or 0,
            }
            for d in resp.items
        ]
