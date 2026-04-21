"""tools/azure/azure_tools.py — Azure VM and Resource Group management tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.azure_client import AzureComputeClient, AzureResourceClient

# ── azure_list_resource_groups ────────────────────────────────────────────────

RG_LIST_TOOL_NAME = "azure_list_resource_groups"
RG_LIST_TOOL_DESCRIPTION = (
    "Lists all Azure resource groups in the subscription. "
    "Shows name, location, provisioning state, and tags. "
    "Requires AZURE_SUBSCRIPTION_ID and Azure credentials."
)
RG_LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def rg_list_handler() -> List[Dict[str, Any]]:
    return AzureResourceClient().list_resource_groups()


# ── azure_list_vms ────────────────────────────────────────────────────────────

VM_LIST_TOOL_NAME = "azure_list_vms"
VM_LIST_TOOL_DESCRIPTION = (
    "Lists Azure Virtual Machines, optionally scoped to a resource group. "
    "Shows VM name, location, size, OS type, and tags."
)
VM_LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "resource_group": {
            "type": "string",
            "description": "Filter to VMs in this resource group (optional — omit for all VMs in subscription).",
        },
    },
    "additionalProperties": False,
}


def vm_list_handler(resource_group: Optional[str] = None) -> List[Dict[str, Any]]:
    return AzureComputeClient().list_vms(resource_group=resource_group)


# ── azure_vm_start ────────────────────────────────────────────────────────────

VM_START_TOOL_NAME = "azure_vm_start"
VM_START_TOOL_DESCRIPTION = "Starts a stopped Azure VM. Waits up to 5 minutes for the operation to complete."
VM_START_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "resource_group": {"type": "string", "description": "Resource group containing the VM."},
        "vm_name": {"type": "string", "description": "Name of the Virtual Machine."},
    },
    "required": ["resource_group", "vm_name"],
    "additionalProperties": False,
}


def vm_start_handler(resource_group: str, vm_name: str) -> Dict[str, Any]:
    return AzureComputeClient().start_vm(resource_group, vm_name)


# ── azure_vm_stop ─────────────────────────────────────────────────────────────

VM_STOP_TOOL_NAME = "azure_vm_stop"
VM_STOP_TOOL_DESCRIPTION = (
    "Stops an Azure VM. With deallocate=true (default) the VM is fully deallocated "
    "so compute charges stop. With deallocate=false the VM is powered off but still billed."
)
VM_STOP_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "resource_group": {"type": "string", "description": "Resource group containing the VM."},
        "vm_name": {"type": "string", "description": "Name of the Virtual Machine."},
        "deallocate": {
            "type": "boolean",
            "description": "Fully deallocate VM to stop billing (default: true).",
            "default": True,
        },
    },
    "required": ["resource_group", "vm_name"],
    "additionalProperties": False,
}


def vm_stop_handler(resource_group: str, vm_name: str, deallocate: bool = True) -> Dict[str, Any]:
    return AzureComputeClient().stop_vm(resource_group, vm_name, deallocate)


# ── azure_aks_list_clusters ───────────────────────────────────────────────────

AKS_LIST_TOOL_NAME = "azure_aks_list_clusters"
AKS_LIST_TOOL_DESCRIPTION = (
    "Lists Azure Kubernetes Service (AKS) clusters in the subscription. "
    "Shows name, location, Kubernetes version, node count, provisioning state, and FQDN."
)
AKS_LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def aks_list_handler() -> List[Dict[str, Any]]:
    from integrations.azure_client import AzureAKSClient
    return AzureAKSClient().list_clusters()


# ── azure_acr_list ────────────────────────────────────────────────────────────

ACR_LIST_TOOL_NAME = "azure_acr_list"
ACR_LIST_TOOL_DESCRIPTION = (
    "Lists Azure Container Registry (ACR) registries in the subscription. "
    "Shows name, login server, SKU, location, and admin status."
)
ACR_LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def acr_list_handler() -> List[Dict[str, Any]]:
    from integrations.azure_client import AzureContainerClient
    return AzureContainerClient().list_registries()


# ── azure_keyvault_get_secret ─────────────────────────────────────────────────

KV_GET_TOOL_NAME = "azure_keyvault_get_secret"
KV_GET_TOOL_DESCRIPTION = (
    "Retrieves a secret from Azure Key Vault. "
    "Requires AZURE_KEYVAULT_URL (e.g. https://my-vault.vault.azure.net/)."
)
KV_GET_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "vault_url": {"type": "string", "description": "Key Vault URL (e.g. https://my-vault.vault.azure.net/)."},
        "secret_name": {"type": "string", "description": "Name of the secret to retrieve."},
    },
    "required": ["vault_url", "secret_name"],
    "additionalProperties": False,
}


def kv_get_handler(vault_url: str, secret_name: str) -> Dict[str, Any]:
    from integrations.azure_client import AzureKeyVaultClient
    return AzureKeyVaultClient(vault_url).get_secret(secret_name)


# ── azure_keyvault_set_secret ─────────────────────────────────────────────────

KV_SET_TOOL_NAME = "azure_keyvault_set_secret"
KV_SET_TOOL_DESCRIPTION = "Creates or updates a secret in Azure Key Vault."
KV_SET_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "vault_url": {"type": "string", "description": "Key Vault URL."},
        "secret_name": {"type": "string", "description": "Secret name."},
        "value": {"type": "string", "description": "Secret value to store."},
    },
    "required": ["vault_url", "secret_name", "value"],
    "additionalProperties": False,
}


def kv_set_handler(vault_url: str, secret_name: str, value: str) -> Dict[str, Any]:
    from integrations.azure_client import AzureKeyVaultClient
    return AzureKeyVaultClient(vault_url).set_secret(secret_name, value)
