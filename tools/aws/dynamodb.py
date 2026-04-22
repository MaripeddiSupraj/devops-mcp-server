"""tools/aws/dynamodb.py — AWS DynamoDB tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.aws_client import DynamoDBClient

# ── aws_dynamodb_list_tables ──────────────────────────────────────────────────

LIST_TABLES_TOOL_NAME = "aws_dynamodb_list_tables"
LIST_TABLES_TOOL_DESCRIPTION = "List all DynamoDB tables in the account."
LIST_TABLES_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def list_tables_handler() -> List[str]:
    return DynamoDBClient().list_tables()


# ── aws_dynamodb_describe_table ───────────────────────────────────────────────

DESCRIBE_TABLE_TOOL_NAME = "aws_dynamodb_describe_table"
DESCRIBE_TABLE_TOOL_DESCRIPTION = "Describe a DynamoDB table — status, item count, key schema, and billing mode."
DESCRIBE_TABLE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "table_name": {"type": "string", "description": "DynamoDB table name."},
    },
    "required": ["table_name"],
    "additionalProperties": False,
}


def describe_table_handler(table_name: str) -> Dict:
    return DynamoDBClient().describe_table(table_name)


# ── aws_dynamodb_get_item ─────────────────────────────────────────────────────

GET_ITEM_TOOL_NAME = "aws_dynamodb_get_item"
GET_ITEM_TOOL_DESCRIPTION = (
    "Get a single item from a DynamoDB table by primary key. "
    "key should be a JSON object with the partition key (and sort key if applicable)."
)
GET_ITEM_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "table_name": {"type": "string", "description": "DynamoDB table name."},
        "key": {
            "type": "object",
            "description": "Primary key as key/value JSON (e.g. {\"id\": \"abc123\"}).",
            "additionalProperties": True,
        },
    },
    "required": ["table_name", "key"],
    "additionalProperties": False,
}


def get_item_handler(table_name: str, key: Dict[str, Any]) -> Optional[Dict]:
    return DynamoDBClient().get_item(table_name, key)


# ── aws_dynamodb_put_item ─────────────────────────────────────────────────────

PUT_ITEM_TOOL_NAME = "aws_dynamodb_put_item"
PUT_ITEM_TOOL_DESCRIPTION = "Put (create or replace) an item in a DynamoDB table."
PUT_ITEM_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "table_name": {"type": "string", "description": "DynamoDB table name."},
        "item": {
            "type": "object",
            "description": "Item attributes as a JSON object.",
            "additionalProperties": True,
        },
    },
    "required": ["table_name", "item"],
    "additionalProperties": False,
}


def put_item_handler(table_name: str, item: Dict[str, Any]) -> Dict:
    return DynamoDBClient().put_item(table_name, item)
