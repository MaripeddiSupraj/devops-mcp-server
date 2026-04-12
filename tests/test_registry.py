"""
tests/test_registry.py
-----------------------
Unit tests for ToolRegistry and build_registry().
"""

from __future__ import annotations

import pytest

from server.registry import ToolEntry, ToolRegistry, build_registry


def _dummy_handler(**kwargs):
    return {"ok": True}


class TestToolRegistry:
    def setup_method(self):
        self.registry = ToolRegistry()

    def test_register_and_get(self):
        entry = ToolEntry(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
            handler=_dummy_handler,
        )
        self.registry.register(entry)
        retrieved = self.registry.get("test_tool")
        assert retrieved is not None
        assert retrieved.name == "test_tool"

    def test_register_duplicate_raises(self):
        entry = ToolEntry(
            name="dup_tool",
            description="dup",
            input_schema={},
            handler=_dummy_handler,
        )
        self.registry.register(entry)
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register(entry)

    def test_get_unknown_returns_none(self):
        assert self.registry.get("nonexistent") is None

    def test_list_names_sorted(self):
        for name in ["z_tool", "a_tool", "m_tool"]:
            self.registry.register(
                ToolEntry(name=name, description="", input_schema={}, handler=_dummy_handler)
            )
        assert self.registry.list_names() == ["a_tool", "m_tool", "z_tool"]

    def test_len(self):
        assert len(self.registry) == 0
        self.registry.register(
            ToolEntry(name="one", description="", input_schema={}, handler=_dummy_handler)
        )
        assert len(self.registry) == 1


class TestBuildRegistry:
    def test_all_tools_registered(self):
        registry = build_registry()
        expected_tools = {
            # Terraform
            "terraform_plan",
            "terraform_apply",
            "terraform_destroy",
            # GitHub
            "github_create_pull_request",
            "github_get_repo",
            # AWS
            "aws_create_ec2_instance",
            "aws_list_ec2_instances",
            "aws_create_s3_bucket",
            "aws_list_s3_buckets",
            # Kubernetes — core
            "k8s_deploy",
            "k8s_get_pods",
            # Kubernetes — extended
            "k8s_get_logs",
            "k8s_get_events",
            "k8s_scale",
            "k8s_rollout_restart",
            "k8s_rollout_status",
            "k8s_get_deployments",
            "k8s_get_services",
            "k8s_get_nodes",
            "k8s_delete_pod",
        }
        registered = set(registry.list_names())
        assert expected_tools == registered

    def test_tool_definitions_have_required_fields(self):
        registry = build_registry()
        for defn in registry.list_definitions():
            assert defn.name
            assert defn.description
            assert isinstance(defn.input_schema, dict)
