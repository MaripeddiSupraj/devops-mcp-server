"""
tools/aws/ec2.py
----------------
MCP tool definitions for EC2 operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.aws_client import ALLOWED_INSTANCE_TYPES, EC2Client

# ── create_ec2_instance ──────────────────────────────────────────────────────

TOOL_NAME = "aws_create_ec2_instance"
TOOL_DESCRIPTION = (
    "Launches a new EC2 instance with the specified configuration. "
    "Instance type must be in the allowed list. "
    "Requires AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Value for the Name tag on the instance.",
        },
        "instance_type": {
            "type": "string",
            "description": f"EC2 instance type. Allowed: {sorted(ALLOWED_INSTANCE_TYPES)}",
            "enum": sorted(ALLOWED_INSTANCE_TYPES),
        },
        "ami_id": {
            "type": "string",
            "description": "Amazon Machine Image ID (e.g. ami-0c55b159cbfafe1f0).",
        },
        "key_name": {
            "type": "string",
            "description": "EC2 Key Pair name for SSH access (optional).",
        },
        "subnet_id": {
            "type": "string",
            "description": "VPC Subnet ID to launch the instance in (optional).",
        },
        "security_group_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of Security Group IDs (optional).",
        },
        "dry_run": {
            "type": "boolean",
            "description": "Validate permissions without actually launching.",
            "default": False,
        },
    },
    "required": ["name", "instance_type", "ami_id"],
    "additionalProperties": False,
}


def handler(
    name: str,
    instance_type: str,
    ami_id: str,
    key_name: Optional[str] = None,
    subnet_id: Optional[str] = None,
    security_group_ids: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Launch a single EC2 instance.

    Returns:
        Dict with ``instance_id``, ``state``, ``instance_type``, ``ami``.
    """
    ec2 = EC2Client()
    return ec2.create_instance(
        name=name,
        instance_type=instance_type,
        ami_id=ami_id,
        key_name=key_name,
        subnet_id=subnet_id,
        security_group_ids=security_group_ids,
        dry_run=dry_run,
    )


# ── list_ec2_instances ────────────────────────────────────────────────────────

LIST_TOOL_NAME = "aws_list_ec2_instances"
LIST_TOOL_DESCRIPTION = "Lists EC2 instances, optionally filtered by state."
LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "state": {
            "type": "string",
            "description": "Filter by instance state (e.g. 'running', 'stopped').",
            "enum": ["pending", "running", "shutting-down", "terminated", "stopping", "stopped"],
        }
    },
    "additionalProperties": False,
}


def list_handler(state: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return a list of EC2 instances, optionally filtered by *state*."""
    ec2 = EC2Client()
    filters = []
    if state:
        filters = [{"Name": "instance-state-name", "Values": [state]}]
    return ec2.list_instances(filters=filters)
