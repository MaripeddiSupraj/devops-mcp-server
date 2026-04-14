"""
tools/aws/lambda_tools.py
--------------------------
MCP tool definitions for AWS Lambda operations.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from integrations.aws_client import LambdaClient

# ── aws_list_lambda_functions ─────────────────────────────────────────────────

TOOL_NAME = "aws_list_lambda_functions"
TOOL_DESCRIPTION = (
    "List all AWS Lambda functions in the configured region. "
    "Returns function name, runtime, handler, memory, timeout, and description."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "max_items": {
            "type": "integer",
            "description": "Maximum number of functions to return (default 50).",
            "default": 50,
            "minimum": 1,
            "maximum": 100,
        }
    },
    "additionalProperties": False,
}


def handler(max_items: int = 50) -> list:
    """Return a list of Lambda functions."""
    return LambdaClient().list_functions(max_items=max_items)


# ── aws_invoke_lambda ─────────────────────────────────────────────────────────

INVOKE_TOOL_NAME = "aws_invoke_lambda"
INVOKE_TOOL_DESCRIPTION = (
    "Invoke an AWS Lambda function synchronously or asynchronously. "
    "Returns the function response, status code, and last 4KB of logs. "
    "Use invocation_type='Event' for fire-and-forget (async) invocations."
)
INVOKE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "function_name": {
            "type": "string",
            "description": "Lambda function name or full ARN.",
        },
        "payload": {
            "type": "object",
            "description": "JSON payload to pass as the Lambda event (optional).",
        },
        "invocation_type": {
            "type": "string",
            "description": "RequestResponse (sync, default), Event (async), or DryRun.",
            "enum": ["RequestResponse", "Event", "DryRun"],
            "default": "RequestResponse",
        },
    },
    "required": ["function_name"],
    "additionalProperties": False,
}


def invoke_handler(
    function_name: str,
    payload: Optional[Dict[str, Any]] = None,
    invocation_type: str = "RequestResponse",
) -> Dict[str, Any]:
    """Invoke a Lambda function and return the response."""
    return LambdaClient().invoke(
        function_name=function_name,
        payload=payload,
        invocation_type=invocation_type,
    )
