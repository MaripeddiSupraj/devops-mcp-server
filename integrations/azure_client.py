"""
integrations/azure_client.py
-----------------------------
Azure SDK client factory using DefaultAzureCredential (supports env vars,
managed identity, CLI auth, and service principal).

Required environment variables (at least one auth path must be set):
  AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET  — service principal
  OR: az login via Azure CLI
  OR: AZURE_SUBSCRIPTION_ID alone with managed identity

AZURE_SUBSCRIPTION_ID is always required.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

from core.auth import get_azure_credentials
from core.logger import get_logger

log = get_logger(__name__)


class AzureClientError(RuntimeError):
    """Wraps Azure SDK exceptions in a domain-specific error."""


@lru_cache(maxsize=1)
def _get_credential():
    from azure.identity import DefaultAzureCredential
    return DefaultAzureCredential()


@lru_cache(maxsize=1)
def _subscription_id() -> str:
    return get_azure_credentials()


class AzureComputeClient:
    """Azure Compute (VM) operations used by MCP tool handlers."""

    def __init__(self) -> None:
        from azure.mgmt.compute import ComputeManagementClient
        self._client = ComputeManagementClient(_get_credential(), _subscription_id())

    def list_vms(self, resource_group: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            if resource_group:
                vms = list(self._client.virtual_machines.list(resource_group))
            else:
                vms = list(self._client.virtual_machines.list_all())
        except Exception as exc:
            raise AzureClientError(f"list_vms failed: {exc}") from exc
        result = []
        for vm in vms:
            result.append({
                "name": vm.name,
                "location": vm.location,
                "resource_group": vm.id.split("/")[4] if vm.id else None,
                "vm_size": vm.hardware_profile.vm_size if vm.hardware_profile else None,
                "os_type": vm.storage_profile.os_disk.os_type if vm.storage_profile and vm.storage_profile.os_disk else None,
                "tags": vm.tags or {},
            })
        return result

    def start_vm(self, resource_group: str, vm_name: str) -> Dict[str, Any]:
        try:
            poller = self._client.virtual_machines.begin_start(resource_group, vm_name)
            poller.result(timeout=300)
        except Exception as exc:
            raise AzureClientError(f"start_vm failed: {exc}") from exc
        log.info("azure_vm_started", resource_group=resource_group, vm=vm_name)
        return {"resource_group": resource_group, "vm_name": vm_name, "action": "start", "status": "succeeded"}

    def stop_vm(self, resource_group: str, vm_name: str, deallocate: bool = True) -> Dict[str, Any]:
        try:
            if deallocate:
                poller = self._client.virtual_machines.begin_deallocate(resource_group, vm_name)
            else:
                poller = self._client.virtual_machines.begin_power_off(resource_group, vm_name)
            poller.result(timeout=300)
        except Exception as exc:
            raise AzureClientError(f"stop_vm failed: {exc}") from exc
        action = "deallocate" if deallocate else "power_off"
        log.info("azure_vm_stopped", resource_group=resource_group, vm=vm_name, action=action)
        return {"resource_group": resource_group, "vm_name": vm_name, "action": action, "status": "succeeded"}


class AzureContainerClient:
    """Azure Container Registry (ACR) operations."""

    def __init__(self) -> None:
        from azure.mgmt.containerregistry import ContainerRegistryManagementClient
        self._client = ContainerRegistryManagementClient(_get_credential(), _subscription_id())

    def list_registries(self) -> List[Dict[str, Any]]:
        try:
            registries = list(self._client.registries.list())
        except Exception as exc:
            raise AzureClientError(f"list_registries failed: {exc}") from exc
        return [
            {
                "name": r.name,
                "location": r.location,
                "login_server": r.login_server,
                "sku": r.sku.name if r.sku else None,
                "admin_enabled": r.admin_user_enabled,
                "resource_group": r.id.split("/")[4] if r.id else None,
            }
            for r in registries
        ]


class AzureAKSClient:
    """Azure Kubernetes Service (AKS) operations."""

    def __init__(self) -> None:
        from azure.mgmt.containerservice import ContainerServiceClient
        self._client = ContainerServiceClient(_get_credential(), _subscription_id())

    def list_clusters(self) -> List[Dict[str, Any]]:
        try:
            clusters = list(self._client.managed_clusters.list())
        except Exception as exc:
            raise AzureClientError(f"list_clusters failed: {exc}") from exc
        return [
            {
                "name": c.name,
                "location": c.location,
                "resource_group": c.id.split("/")[4] if c.id else None,
                "k8s_version": c.kubernetes_version,
                "provisioning_state": c.provisioning_state,
                "node_count": sum(p.count or 0 for p in (c.agent_pool_profiles or [])),
                "fqdn": c.fqdn,
            }
            for c in clusters
        ]


class AzureKeyVaultClient:
    """Azure Key Vault secret operations."""

    def __init__(self, vault_url: str) -> None:
        from azure.keyvault.secrets import SecretClient
        self._client = SecretClient(vault_url=vault_url, credential=_get_credential())
        self._vault_url = vault_url

    def get_secret(self, name: str) -> Dict[str, Any]:
        try:
            secret = self._client.get_secret(name)
        except Exception as exc:
            raise AzureClientError(f"get_secret failed: {exc}") from exc
        log.info("azure_keyvault_secret_retrieved", name=name, vault=self._vault_url)
        return {"name": secret.name, "value": secret.value, "version": secret.properties.version, "enabled": secret.properties.enabled}

    def set_secret(self, name: str, value: str) -> Dict[str, Any]:
        try:
            secret = self._client.set_secret(name, value)
        except Exception as exc:
            raise AzureClientError(f"set_secret failed: {exc}") from exc
        log.info("azure_keyvault_secret_set", name=name, vault=self._vault_url)
        return {"name": secret.name, "version": secret.properties.version, "enabled": secret.properties.enabled}


class AzureResourceClient:
    """Azure Resource Group operations used by MCP tool handlers."""

    def __init__(self) -> None:
        from azure.mgmt.resource import ResourceManagementClient
        self._client = ResourceManagementClient(_get_credential(), _subscription_id())

    def list_resource_groups(self) -> List[Dict[str, Any]]:
        try:
            groups = list(self._client.resource_groups.list())
        except Exception as exc:
            raise AzureClientError(f"list_resource_groups failed: {exc}") from exc
        return [
            {
                "name": g.name,
                "location": g.location,
                "state": g.properties.provisioning_state if g.properties else None,
                "tags": g.tags or {},
            }
            for g in groups
        ]


class AzureCostClient:
    """Azure Cost Management — spend analysis."""

    def __init__(self) -> None:
        creds = get_azure_credentials()
        self._subscription_id = creds["subscription_id"]
        from azure.identity import DefaultAzureCredential
        self._credential = DefaultAzureCredential()

    def get_cost_by_service(self, start_date: str, end_date: str) -> Dict[str, Any]:
        try:
            from azure.mgmt.costmanagement import CostManagementClient
            from azure.mgmt.costmanagement.models import (
                QueryDefinition, QueryTimePeriod, QueryDataset, QueryAggregation, QueryGrouping, TimeframeType
            )
            client = CostManagementClient(self._credential)
            scope = f"/subscriptions/{self._subscription_id}"
            query = QueryDefinition(
                type="ActualCost",
                timeframe=TimeframeType.CUSTOM,
                time_period=QueryTimePeriod(from_property=start_date, to=end_date),
                dataset=QueryDataset(
                    granularity="None",
                    aggregation={"totalCost": QueryAggregation(name="Cost", function="Sum")},
                    grouping=[QueryGrouping(type="Dimension", name="ServiceName")],
                ),
            )
            result = client.query.usage(scope=scope, parameters=query)
        except Exception as exc:
            raise AzureClientError(f"get_cost_by_service failed: {exc}") from exc
        rows = result.rows or []
        columns = [c.name for c in (result.columns or [])]
        return {
            "start_date": start_date,
            "end_date": end_date,
            "breakdown": [dict(zip(columns, row)) for row in rows],
        }
