"""tools/aws/networking.py — VPC, Security Group, and Route53 tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.aws_client import NetworkingClient

# ── aws_vpc_list ─────────────────────────────────────────────────────────────

VPC_LIST_TOOL_NAME = "aws_vpc_list"
VPC_LIST_TOOL_DESCRIPTION = (
    "Lists all VPCs in the current AWS region. "
    "Shows VPC ID, CIDR block, state, whether it is the default VPC, and Name tag."
)
VPC_LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def vpc_list_handler() -> List[Dict[str, Any]]:
    return NetworkingClient().list_vpcs()


# ── aws_security_group_list ───────────────────────────────────────────────────

SG_LIST_TOOL_NAME = "aws_security_group_list"
SG_LIST_TOOL_DESCRIPTION = (
    "Lists security groups, optionally filtered by VPC. "
    "Shows group ID, name, description, VPC, and inbound/outbound rule counts."
)
SG_LIST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "vpc_id": {"type": "string", "description": "Filter to security groups in this VPC (optional)."},
    },
    "additionalProperties": False,
}


def sg_list_handler(vpc_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return NetworkingClient().list_security_groups(vpc_id=vpc_id)


# ── aws_route53_list_zones ────────────────────────────────────────────────────

R53_TOOL_NAME = "aws_route53_list_zones"
R53_TOOL_DESCRIPTION = (
    "Lists all Route53 hosted zones in the account. "
    "Shows zone ID, domain name, public/private flag, and record count."
)
R53_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def r53_list_handler() -> List[Dict[str, Any]]:
    return NetworkingClient().list_hosted_zones()
