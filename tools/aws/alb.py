"""tools/aws/alb.py — AWS Application Load Balancer tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.aws_client import ALBClient

# ── aws_alb_list ──────────────────────────────────────────────────────────────

ALB_LIST_TOOL_NAME = "aws_alb_list"
ALB_LIST_TOOL_DESCRIPTION = (
    "Lists Application and Network Load Balancers in the current region. "
    "Shows name, DNS name, scheme (internet-facing/internal), type, state, and VPC."
)
ALB_LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def alb_list_handler() -> List[Dict[str, Any]]:
    return ALBClient().list_load_balancers()


# ── aws_alb_target_groups ─────────────────────────────────────────────────────

TG_LIST_TOOL_NAME = "aws_alb_target_groups"
TG_LIST_TOOL_DESCRIPTION = (
    "Lists target groups, optionally scoped to a specific load balancer ARN. "
    "Shows name, protocol, port, target type, and health check path."
)
TG_LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "load_balancer_arn": {
            "type": "string",
            "description": "Filter to target groups attached to this load balancer ARN (optional).",
        },
    },
    "additionalProperties": False,
}


def tg_list_handler(load_balancer_arn: Optional[str] = None) -> List[Dict[str, Any]]:
    return ALBClient().list_target_groups(load_balancer_arn)
