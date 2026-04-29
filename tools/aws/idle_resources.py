"""tools/aws/idle_resources.py — Detect idle/wasted AWS resources."""

from __future__ import annotations

from typing import Any, Dict

from integrations.idle_resources_client import IdleResourcesClient

TOOL_NAME = "aws_find_idle_resources"
TOOL_DESCRIPTION = (
    "Scans your AWS account for idle and wasted resources: "
    "EC2 instances with low CPU utilisation, stopped or idle RDS instances, "
    "and unattached EBS volumes. "
    "Returns a summary and full list of idle resources with reasons. "
    "Requires AWS credentials and CloudWatch read access."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "cpu_threshold_pct": {
            "type": "number",
            "description": "CPU utilisation % below which an instance is considered idle (default: 5).",
            "default": 5.0,
        },
        "lookback_days": {
            "type": "integer",
            "description": "How many days of CloudWatch CPU data to average (default: 7).",
            "default": 7,
        },
    },
    "additionalProperties": False,
}


def handler(
    cpu_threshold_pct: float = 5.0,
    lookback_days: int = 7,
) -> Dict[str, Any]:
    """
    Find idle EC2 instances, stopped/idle RDS instances, and unattached EBS volumes.

    Returns:
        Dict with ``summary``, ``idle_ec2``, ``idle_rds``, ``unattached_ebs``.
    """
    client = IdleResourcesClient(cpu_threshold=cpu_threshold_pct, days=lookback_days)
    return client.find_all()
