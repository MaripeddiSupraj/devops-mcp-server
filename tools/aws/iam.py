"""tools/aws/iam.py — AWS IAM tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.aws_client import IAMClient

# ── aws_iam_list_roles ────────────────────────────────────────────────────────

LIST_ROLES_TOOL_NAME = "aws_iam_list_roles"
LIST_ROLES_TOOL_DESCRIPTION = (
    "Lists IAM roles in the account, optionally filtered by path prefix. "
    "Shows name, ARN, path, creation date, and description."
)
LIST_ROLES_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "prefix": {"type": "string", "description": "IAM path prefix filter (e.g. '/service-role/')."},
    },
    "additionalProperties": False,
}


def list_roles_handler(prefix: Optional[str] = None) -> List[Dict[str, Any]]:
    return IAMClient().list_roles(prefix=prefix)


# ── aws_iam_list_policies ─────────────────────────────────────────────────────

LIST_POLICIES_TOOL_NAME = "aws_iam_list_policies"
LIST_POLICIES_TOOL_DESCRIPTION = (
    "Lists IAM policies. scope='Local' returns customer-managed policies only; "
    "'AWS' returns AWS-managed; 'All' returns both."
)
LIST_POLICIES_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "scope": {
            "type": "string",
            "enum": ["Local", "AWS", "All"],
            "description": "Policy scope filter (default: Local — customer-managed only).",
            "default": "Local",
        },
    },
    "additionalProperties": False,
}


def list_policies_handler(scope: str = "Local") -> List[Dict[str, Any]]:
    return IAMClient().list_policies(scope=scope)


# ── aws_iam_simulate_policy ───────────────────────────────────────────────────

SIMULATE_TOOL_NAME = "aws_iam_simulate_policy"
SIMULATE_TOOL_DESCRIPTION = (
    "Simulates whether a policy grants specific actions on given resources. "
    "Returns Allow/Deny/ImplicitDeny per action/resource pair. "
    "Useful for debugging permission issues without making real API calls."
)
SIMULATE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "policy_arn": {"type": "string", "description": "ARN of the IAM role or policy to simulate."},
        "actions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "IAM actions to test (e.g. ['s3:GetObject', 'ec2:DescribeInstances']).",
        },
        "resource_arns": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Resource ARNs to test against (e.g. ['arn:aws:s3:::my-bucket/*']).",
        },
    },
    "required": ["policy_arn", "actions", "resource_arns"],
    "additionalProperties": False,
}


def simulate_handler(policy_arn: str, actions: List[str], resource_arns: List[str]) -> List[Dict[str, Any]]:
    return IAMClient().simulate_policy(policy_arn, actions, resource_arns)
