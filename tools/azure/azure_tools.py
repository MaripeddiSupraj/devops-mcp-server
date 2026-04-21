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
