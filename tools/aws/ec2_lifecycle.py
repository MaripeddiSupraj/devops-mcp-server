"""tools/aws/ec2_lifecycle.py — stop, start, terminate EC2 instances."""

from __future__ import annotations

from typing import Any, Dict

from integrations.aws_client import EC2Client

# ── aws_ec2_stop ─────────────────────────────────────────────────────────────

STOP_TOOL_NAME = "aws_ec2_stop"
STOP_TOOL_DESCRIPTION = (
    "Stops a running EC2 instance. The instance can be restarted later. "
    "EBS-backed instances retain their data when stopped."
)
STOP_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "instance_id": {"type": "string", "description": "EC2 instance ID (e.g. i-0abc123)."},
    },
    "required": ["instance_id"],
    "additionalProperties": False,
}


def stop_handler(instance_id: str) -> Dict[str, Any]:
    return EC2Client().stop_instance(instance_id)


# ── aws_ec2_start ────────────────────────────────────────────────────────────

START_TOOL_NAME = "aws_ec2_start"
START_TOOL_DESCRIPTION = "Starts a stopped EC2 instance."
START_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "instance_id": {"type": "string", "description": "EC2 instance ID (e.g. i-0abc123)."},
    },
    "required": ["instance_id"],
    "additionalProperties": False,
}


def start_handler(instance_id: str) -> Dict[str, Any]:
    return EC2Client().start_instance(instance_id)


# ── aws_ec2_terminate ────────────────────────────────────────────────────────

TERMINATE_TOOL_NAME = "aws_ec2_terminate"
TERMINATE_TOOL_DESCRIPTION = (
    "Permanently terminates an EC2 instance. THIS IS IRREVERSIBLE. "
    "You must pass confirm_terminate='TERMINATE' to proceed."
)
TERMINATE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "instance_id": {"type": "string", "description": "EC2 instance ID (e.g. i-0abc123)."},
        "confirm_terminate": {
            "type": "string",
            "description": "Must be exactly 'TERMINATE' to confirm the irreversible action.",
        },
    },
    "required": ["instance_id", "confirm_terminate"],
    "additionalProperties": False,
}


def terminate_handler(instance_id: str, confirm_terminate: str) -> Dict[str, Any]:
    if confirm_terminate != "TERMINATE":
        return {
            "status": "blocked",
            "reason": "confirm_terminate must be exactly 'TERMINATE' to proceed.",
        }
    return EC2Client().terminate_instance(instance_id)
