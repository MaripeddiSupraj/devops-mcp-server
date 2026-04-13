"""
tests/test_tools_k8s.py
------------------------
Unit tests for Kubernetes tool handlers using mocked kubernetes client.

The kubernetes API client is patched at integrations.k8s_client.k8s_client
(imported as `from kubernetes import client as k8s_client`).
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


def _make_pod(
    name="web-7d6f4b8d9c-xk2pq",
    namespace="default",
    phase="Running",
    ready=True,
    restarts=0,
    node="node-1",
    ip="10.0.0.5",
):
    pod = MagicMock()
    pod.metadata.name = name
    pod.metadata.namespace = namespace
    pod.status.phase = phase
    pod.spec.node_name = node
    pod.status.pod_ip = ip
    container_status = MagicMock()
    container_status.ready = ready
    container_status.restart_count = restarts
    pod.status.container_statuses = [container_status]
    return pod


def _make_node(name="node-1", ready=True, cpu="4", memory="8Gi", version="v1.28"):
    node = MagicMock()
    node.metadata.name = name
    node.status.capacity = {"cpu": cpu, "memory": memory}
    node.status.node_info.kubelet_version = version
    cond = MagicMock()
    cond.type = "Ready"
    cond.status = "True" if ready else "False"
    node.status.conditions = [cond]
    return node


def _make_deployment(name="web", namespace="default", desired=3, ready=3):
    dep = MagicMock()
    dep.metadata.name = name
    dep.metadata.namespace = namespace
    dep.spec.replicas = desired
    dep.status.ready_replicas = ready
    dep.status.available_replicas = ready
    dep.metadata.creation_timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return dep


def _k8s_client_ctx(core=None, apps=None):
    """Patch k8s_client so CoreV1Api/AppsV1Api return controlled mocks."""
    mock_lib = MagicMock()
    if core:
        mock_lib.CoreV1Api.return_value = core
    if apps:
        mock_lib.AppsV1Api.return_value = apps
    return patch("integrations.k8s_client.k8s_client", mock_lib), mock_lib


# ── k8s_get_pods ──────────────────────────────────────────────────────────────

class TestGetPods:
    @patch("integrations.k8s_client._get_k8s_config")
    def test_returns_list_with_pod_info(self, _cfg):
        mock_core = MagicMock()
        pod = _make_pod()
        mock_core.list_namespaced_pod.return_value.items = [pod]
        mock_core.list_namespaced_pod.return_value.metadata._continue = None
        patcher, _ = _k8s_client_ctx(core=mock_core)
        with patcher:
            from integrations.k8s_client import KubernetesClient
            result = KubernetesClient().get_pods("default")
        assert len(result) == 1
        assert result[0]["name"] == "web-7d6f4b8d9c-xk2pq"
        assert result[0]["ready"] is True
        assert result[0]["restarts"] == 0

    @patch("integrations.k8s_client._get_k8s_config")
    def test_empty_namespace_returns_empty_list(self, _cfg):
        mock_core = MagicMock()
        mock_core.list_namespaced_pod.return_value.items = []
        mock_core.list_namespaced_pod.return_value.metadata._continue = None
        patcher, _ = _k8s_client_ctx(core=mock_core)
        with patcher:
            from integrations.k8s_client import KubernetesClient
            result = KubernetesClient().get_pods("empty-ns")
        assert result == []

    @patch("integrations.k8s_client._get_k8s_config")
    def test_crashloop_pod_shows_not_ready(self, _cfg):
        mock_core = MagicMock()
        pod = _make_pod(phase="CrashLoopBackOff", ready=False, restarts=15)
        mock_core.list_namespaced_pod.return_value.items = [pod]
        mock_core.list_namespaced_pod.return_value.metadata._continue = None
        patcher, _ = _k8s_client_ctx(core=mock_core)
        with patcher:
            from integrations.k8s_client import KubernetesClient
            result = KubernetesClient().get_pods("default")
        assert result[0]["ready"] is False
        assert result[0]["restarts"] == 15

    @patch("integrations.k8s_client._get_k8s_config")
    def test_multiple_pods_returned(self, _cfg):
        mock_core = MagicMock()
        pods = [_make_pod(name=f"pod-{i}") for i in range(5)]
        mock_core.list_namespaced_pod.return_value.items = pods
        mock_core.list_namespaced_pod.return_value.metadata._continue = None
        patcher, _ = _k8s_client_ctx(core=mock_core)
        with patcher:
            from integrations.k8s_client import KubernetesClient
            result = KubernetesClient().get_pods("default")
        assert len(result) == 5


# ── k8s_get_nodes ─────────────────────────────────────────────────────────────

class TestGetNodes:
    @patch("integrations.k8s_client._get_k8s_config")
    def test_returns_node_list(self, _cfg):
        mock_core = MagicMock()
        node = _make_node()
        mock_core.list_node.return_value.items = [node]
        mock_core.list_node.return_value.metadata._continue = None
        patcher, _ = _k8s_client_ctx(core=mock_core)
        with patcher:
            from integrations.k8s_client import KubernetesClient
            result = KubernetesClient().get_nodes()
        assert len(result) == 1
        assert result[0]["name"] == "node-1"
        assert result[0]["ready"] is True
        assert result[0]["cpu"] == "4"

    @patch("integrations.k8s_client._get_k8s_config")
    def test_not_ready_node_flagged(self, _cfg):
        mock_core = MagicMock()
        node = _make_node(ready=False)
        mock_core.list_node.return_value.items = [node]
        mock_core.list_node.return_value.metadata._continue = None
        patcher, _ = _k8s_client_ctx(core=mock_core)
        with patcher:
            from integrations.k8s_client import KubernetesClient
            result = KubernetesClient().get_nodes()
        assert result[0]["ready"] is False


# ── k8s_scale ─────────────────────────────────────────────────────────────────

class TestScaleDeployment:
    @patch("integrations.k8s_client._get_k8s_config")
    def test_scale_calls_patch_api(self, _cfg):
        mock_apps = MagicMock()
        dep = _make_deployment(desired=5, ready=5)
        mock_apps.patch_namespaced_deployment_scale.return_value = dep
        patcher, _ = _k8s_client_ctx(apps=mock_apps)
        with patcher:
            from integrations.k8s_client import KubernetesClient
            result = KubernetesClient().scale_deployment("web", "default", replicas=5)
        mock_apps.patch_namespaced_deployment_scale.assert_called_once()
        assert result["replicas"] == 5

    @patch("integrations.k8s_client._get_k8s_config")
    def test_scale_to_zero(self, _cfg):
        mock_apps = MagicMock()
        dep = _make_deployment(desired=0, ready=0)
        mock_apps.patch_namespaced_deployment_scale.return_value = dep
        patcher, _ = _k8s_client_ctx(apps=mock_apps)
        with patcher:
            from integrations.k8s_client import KubernetesClient
            KubernetesClient().scale_deployment("web", "default", replicas=0)
        call_body = mock_apps.patch_namespaced_deployment_scale.call_args[1]["body"]
        assert call_body["spec"]["replicas"] == 0


# ── k8s_get_logs ──────────────────────────────────────────────────────────────

class TestGetLogs:
    @patch("integrations.k8s_client._get_k8s_config")
    def test_returns_log_string(self, _cfg):
        mock_core = MagicMock()
        mock_core.read_namespaced_pod_log.return_value = "INFO: server started\n"
        patcher, _ = _k8s_client_ctx(core=mock_core)
        with patcher:
            from integrations.k8s_client import KubernetesClient
            result = KubernetesClient().get_logs("web-pod", "default", tail_lines=100)
        assert "server started" in result["logs"]

    @patch("integrations.k8s_client._get_k8s_config")
    def test_tail_lines_forwarded(self, _cfg):
        mock_core = MagicMock()
        mock_core.read_namespaced_pod_log.return_value = ""
        patcher, _ = _k8s_client_ctx(core=mock_core)
        with patcher:
            from integrations.k8s_client import KubernetesClient
            KubernetesClient().get_logs("web-pod", "default", tail_lines=50)
        kwargs = mock_core.read_namespaced_pod_log.call_args[1]
        assert kwargs.get("tail_lines") == 50


# ── k8s_delete_pod ────────────────────────────────────────────────────────────

class TestDeletePod:
    @patch("integrations.k8s_client._get_k8s_config")
    def test_delete_pod_calls_api(self, _cfg):
        mock_core = MagicMock()
        patcher, _ = _k8s_client_ctx(core=mock_core)
        with patcher:
            from integrations.k8s_client import KubernetesClient
            result = KubernetesClient().delete_pod("web-pod-abc", "default")
        mock_core.delete_namespaced_pod.assert_called_once()
        assert result["deleted"] == "web-pod-abc"


# ── k8s_get_deployments ───────────────────────────────────────────────────────

class TestGetDeployments:
    @patch("integrations.k8s_client._get_k8s_config")
    def test_returns_deployment_list(self, _cfg):
        mock_apps = MagicMock()
        dep = _make_deployment()
        mock_apps.list_namespaced_deployment.return_value.items = [dep]
        mock_apps.list_namespaced_deployment.return_value.metadata._continue = None
        patcher, _ = _k8s_client_ctx(apps=mock_apps)
        with patcher:
            from integrations.k8s_client import KubernetesClient
            result = KubernetesClient().get_deployments("default")
        assert len(result) == 1
        assert result[0]["name"] == "web"
        assert result[0]["desired"] == 3
        assert result[0]["ready"] == 3
