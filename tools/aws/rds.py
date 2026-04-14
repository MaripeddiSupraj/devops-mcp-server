"""
tools/aws/rds.py
-----------------
MCP tool definitions for AWS RDS operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.aws_client import RDSClient

# ── aws_list_rds_instances ────────────────────────────────────────────────────

TOOL_NAME = "aws_list_rds_instances"
TOOL_DESCRIPTION = (
    "List AWS RDS database instances. Returns identifier, engine, version, "
    "status, instance class, endpoint, port, Multi-AZ flag, and allocated storage. "
    "Optionally filter by a specific DB instance identifier."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "db_instance_identifier": {
            "type": "string",
            "description": "Filter to a specific RDS instance by identifier (optional).",
        }
    },
    "additionalProperties": False,
}


def handler(db_instance_identifier: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return a list of RDS instances, optionally filtered by identifier."""
    return RDSClient().list_instances(db_instance_identifier=db_instance_identifier)
