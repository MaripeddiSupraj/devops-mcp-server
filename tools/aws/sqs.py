"""tools/aws/sqs.py — AWS SQS tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.aws_client import SQSClient

# ── aws_sqs_list_queues ───────────────────────────────────────────────────────

LIST_QUEUES_TOOL_NAME = "aws_sqs_list_queues"
LIST_QUEUES_TOOL_DESCRIPTION = "List SQS queues in the account, optionally filtered by name prefix."
LIST_QUEUES_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "prefix": {"type": "string", "description": "Queue name prefix to filter (optional)."},
    },
    "additionalProperties": False,
}


def list_queues_handler(prefix: Optional[str] = None) -> List[Dict]:
    return SQSClient().list_queues(prefix=prefix)


# ── aws_sqs_send_message ──────────────────────────────────────────────────────

SEND_MESSAGE_TOOL_NAME = "aws_sqs_send_message"
SEND_MESSAGE_TOOL_DESCRIPTION = "Send a message to an SQS queue by URL."
SEND_MESSAGE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "queue_url": {"type": "string", "description": "Full SQS queue URL."},
        "body": {"type": "string", "description": "Message body."},
        "delay_seconds": {"type": "integer", "description": "Delivery delay in seconds (0-900, default 0).", "default": 0},
    },
    "required": ["queue_url", "body"],
    "additionalProperties": False,
}


def send_message_handler(queue_url: str, body: str, delay_seconds: int = 0) -> Dict:
    return SQSClient().send_message(queue_url, body, delay_seconds=delay_seconds)


# ── aws_sqs_get_queue_attributes ──────────────────────────────────────────────

GET_ATTRS_TOOL_NAME = "aws_sqs_get_queue_attributes"
GET_ATTRS_TOOL_DESCRIPTION = "Get attributes for an SQS queue — message count, ARN, creation time, etc."
GET_ATTRS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "queue_url": {"type": "string", "description": "Full SQS queue URL."},
    },
    "required": ["queue_url"],
    "additionalProperties": False,
}


def get_attrs_handler(queue_url: str) -> Dict:
    return SQSClient().get_queue_attributes(queue_url)


# ── aws_sqs_purge_queue ───────────────────────────────────────────────────────

PURGE_QUEUE_TOOL_NAME = "aws_sqs_purge_queue"
PURGE_QUEUE_TOOL_DESCRIPTION = "Purge all messages from an SQS queue. This action is irreversible."
PURGE_QUEUE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "queue_url": {"type": "string", "description": "Full SQS queue URL to purge."},
    },
    "required": ["queue_url"],
    "additionalProperties": False,
}


def purge_queue_handler(queue_url: str) -> Dict:
    return SQSClient().purge_queue(queue_url)
