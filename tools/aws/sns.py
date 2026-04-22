"""tools/aws/sns.py — AWS SNS tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.aws_client import SNSClient

# ── aws_sns_list_topics ───────────────────────────────────────────────────────

LIST_TOPICS_TOOL_NAME = "aws_sns_list_topics"
LIST_TOPICS_TOOL_DESCRIPTION = "List all SNS topics in the account with their ARNs."
LIST_TOPICS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def list_topics_handler() -> List[Dict]:
    return SNSClient().list_topics()


# ── aws_sns_publish ───────────────────────────────────────────────────────────

PUBLISH_TOOL_NAME = "aws_sns_publish"
PUBLISH_TOOL_DESCRIPTION = "Publish a message to an SNS topic."
PUBLISH_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "topic_arn": {"type": "string", "description": "ARN of the SNS topic."},
        "message": {"type": "string", "description": "Message body to publish."},
        "subject": {"type": "string", "description": "Optional subject (used for email subscribers)."},
    },
    "required": ["topic_arn", "message"],
    "additionalProperties": False,
}


def publish_handler(topic_arn: str, message: str, subject: Optional[str] = None) -> Dict:
    return SNSClient().publish(topic_arn, message, subject=subject)


# ── aws_sns_list_subscriptions ────────────────────────────────────────────────

LIST_SUBS_TOOL_NAME = "aws_sns_list_subscriptions"
LIST_SUBS_TOOL_DESCRIPTION = "List subscriptions for an SNS topic, or all subscriptions if no topic_arn is provided."
LIST_SUBS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "topic_arn": {"type": "string", "description": "SNS topic ARN (optional — omit for all subscriptions)."},
    },
    "additionalProperties": False,
}


def list_subs_handler(topic_arn: Optional[str] = None) -> List[Dict]:
    return SNSClient().list_subscriptions(topic_arn=topic_arn)
