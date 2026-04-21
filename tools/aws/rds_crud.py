"""tools/aws/rds_crud.py — RDS create, snapshot, and restore tools."""

from __future__ import annotations

from typing import Any, Dict

from integrations.aws_client import RDSClient

# ── aws_rds_create ────────────────────────────────────────────────────────────

CREATE_TOOL_NAME = "aws_rds_create"
CREATE_TOOL_DESCRIPTION = (
    "Creates a new RDS database instance. "
    "Supported engines: mysql, postgres, mariadb, oracle-se2, sqlserver-ex. "
    "The instance will take several minutes to become available."
)
CREATE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "identifier": {"type": "string", "description": "Unique DB instance identifier."},
        "engine": {
            "type": "string",
            "enum": ["mysql", "postgres", "mariadb", "oracle-se2", "sqlserver-ex"],
            "description": "Database engine.",
        },
        "instance_class": {"type": "string", "description": "DB instance class (e.g. db.t3.micro).", "default": "db.t3.micro"},
        "master_username": {"type": "string", "description": "Master database username."},
        "master_password": {"type": "string", "description": "Master database password (min 8 chars)."},
        "allocated_storage": {"type": "integer", "description": "Storage in GB (default: 20).", "default": 20},
        "multi_az": {"type": "boolean", "description": "Enable Multi-AZ deployment for high availability.", "default": False},
    },
    "required": ["identifier", "engine", "master_username", "master_password"],
    "additionalProperties": False,
}


def create_handler(
    identifier: str,
    engine: str,
    master_username: str,
    master_password: str,
    instance_class: str = "db.t3.micro",
    allocated_storage: int = 20,
    multi_az: bool = False,
) -> Dict[str, Any]:
    return RDSClient().create_instance(identifier, engine, instance_class, master_username, master_password, allocated_storage, multi_az)


# ── aws_rds_snapshot ──────────────────────────────────────────────────────────

SNAPSHOT_TOOL_NAME = "aws_rds_snapshot"
SNAPSHOT_TOOL_DESCRIPTION = (
    "Creates a manual snapshot of an RDS instance. "
    "Snapshots can be used to restore a new instance at any time."
)
SNAPSHOT_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "identifier": {"type": "string", "description": "Source DB instance identifier."},
        "snapshot_identifier": {"type": "string", "description": "Unique name for the snapshot."},
    },
    "required": ["identifier", "snapshot_identifier"],
    "additionalProperties": False,
}


def snapshot_handler(identifier: str, snapshot_identifier: str) -> Dict[str, Any]:
    return RDSClient().create_snapshot(identifier, snapshot_identifier)


# ── aws_rds_restore ───────────────────────────────────────────────────────────

RESTORE_TOOL_NAME = "aws_rds_restore"
RESTORE_TOOL_DESCRIPTION = (
    "Restores a new RDS instance from an existing snapshot. "
    "The original instance is not affected."
)
RESTORE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "snapshot_identifier": {"type": "string", "description": "Snapshot to restore from."},
        "target_identifier": {"type": "string", "description": "New DB instance identifier for the restored instance."},
        "instance_class": {"type": "string", "description": "DB instance class for the restored instance.", "default": "db.t3.micro"},
    },
    "required": ["snapshot_identifier", "target_identifier"],
    "additionalProperties": False,
}


def restore_handler(snapshot_identifier: str, target_identifier: str, instance_class: str = "db.t3.micro") -> Dict[str, Any]:
    return RDSClient().restore_from_snapshot(snapshot_identifier, target_identifier, instance_class)
