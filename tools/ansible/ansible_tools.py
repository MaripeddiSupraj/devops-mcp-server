"""tools/ansible/ansible_tools.py — Ansible automation tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.ansible_runner import AnsibleRunner

# ── ansible_run_playbook ──────────────────────────────────────────────────────

RUN_PLAYBOOK_TOOL_NAME = "ansible_run_playbook"
RUN_PLAYBOOK_TOOL_DESCRIPTION = (
    "Run an Ansible playbook. Returns stdout output. "
    "Set check=true for dry-run mode (--check). "
    "Requires ansible-playbook binary on PATH."
)
RUN_PLAYBOOK_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "playbook": {"type": "string", "description": "Absolute path to the playbook YAML file."},
        "inventory": {"type": "string", "description": "Path to inventory file or directory (optional)."},
        "extra_vars": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "description": "Extra variables to pass with -e (optional).",
        },
        "limit": {"type": "string", "description": "Limit execution to a specific host or group pattern (optional)."},
        "tags": {"type": "string", "description": "Comma-separated tags to run (optional)."},
        "check": {"type": "boolean", "description": "Run in check (dry-run) mode (default: false).", "default": False},
    },
    "required": ["playbook"],
    "additionalProperties": False,
}


def run_playbook_handler(
    playbook: str,
    inventory: Optional[str] = None,
    extra_vars: Optional[Dict[str, str]] = None,
    limit: Optional[str] = None,
    tags: Optional[str] = None,
    check: bool = False,
) -> Dict:
    output = AnsibleRunner().run_playbook(
        playbook, inventory=inventory, extra_vars=extra_vars, limit=limit, tags=tags, check=check
    )
    return {"playbook": playbook, "check_mode": check, "output": output}


# ── ansible_list_hosts ────────────────────────────────────────────────────────

LIST_HOSTS_TOOL_NAME = "ansible_list_hosts"
LIST_HOSTS_TOOL_DESCRIPTION = "List hosts in an Ansible inventory matching a pattern."
LIST_HOSTS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "inventory": {"type": "string", "description": "Path to inventory file or directory."},
        "pattern": {"type": "string", "description": "Host pattern (default: 'all').", "default": "all"},
    },
    "required": ["inventory"],
    "additionalProperties": False,
}


def list_hosts_handler(inventory: str, pattern: str = "all") -> List[str]:
    return AnsibleRunner().list_hosts(inventory, pattern=pattern)


# ── ansible_ping ──────────────────────────────────────────────────────────────

PING_TOOL_NAME = "ansible_ping"
PING_TOOL_DESCRIPTION = "Run an Ansible ping against hosts in inventory to verify connectivity."
PING_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "inventory": {"type": "string", "description": "Path to inventory file or directory."},
        "pattern": {"type": "string", "description": "Host pattern (default: 'all').", "default": "all"},
    },
    "required": ["inventory"],
    "additionalProperties": False,
}


def ping_handler(inventory: str, pattern: str = "all") -> Dict:
    output = AnsibleRunner().ping(inventory, pattern=pattern)
    return {"inventory": inventory, "pattern": pattern, "output": output}


# ── ansible_run_module ────────────────────────────────────────────────────────

RUN_MODULE_TOOL_NAME = "ansible_run_module"
RUN_MODULE_TOOL_DESCRIPTION = (
    "Run an ad-hoc Ansible module against hosts (e.g. shell, command, copy, service). "
    "Equivalent to: ansible -i inventory pattern -m module -a args"
)
RUN_MODULE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "inventory": {"type": "string", "description": "Path to inventory file or directory."},
        "pattern": {"type": "string", "description": "Host pattern to target."},
        "module": {"type": "string", "description": "Ansible module name (e.g. 'shell', 'copy', 'service')."},
        "args": {"type": "string", "description": "Module arguments string (optional)."},
    },
    "required": ["inventory", "pattern", "module"],
    "additionalProperties": False,
}


def run_module_handler(inventory: str, pattern: str, module: str, args: Optional[str] = None) -> Dict:
    output = AnsibleRunner().run_module(inventory, pattern, module, args=args)
    return {"inventory": inventory, "pattern": pattern, "module": module, "output": output}
