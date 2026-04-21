"""tools/aws/cloudwatch.py — CloudWatch metrics, alarms, and log tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.aws_client import CloudWatchClient

# ── aws_cloudwatch_get_metrics ───────────────────────────────────────────────

GET_METRICS_TOOL_NAME = "aws_cloudwatch_get_metrics"
GET_METRICS_TOOL_DESCRIPTION = (
    "Fetches CloudWatch metric datapoints for a given namespace and metric. "
    "Examples: CPU utilisation for EC2, Invocations for Lambda, FreeStorageSpace for RDS."
)
GET_METRICS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "namespace": {"type": "string", "description": "CloudWatch namespace (e.g. 'AWS/EC2', 'AWS/Lambda')."},
        "metric_name": {"type": "string", "description": "Metric name (e.g. 'CPUUtilization', 'Invocations')."},
        "dimensions": {
            "type": "array",
            "description": "List of {Name, Value} dimension filters (e.g. [{Name: InstanceId, Value: i-0abc}]).",
            "items": {
                "type": "object",
                "properties": {"Name": {"type": "string"}, "Value": {"type": "string"}},
                "required": ["Name", "Value"],
            },
        },
        "period": {"type": "integer", "description": "Aggregation period in seconds (default: 300).", "default": 300},
        "stat": {
            "type": "string",
            "description": "Statistic to retrieve.",
            "enum": ["Average", "Sum", "Minimum", "Maximum", "SampleCount"],
            "default": "Average",
        },
        "hours": {"type": "integer", "description": "How many hours back to fetch (default: 1).", "default": 1},
    },
    "required": ["namespace", "metric_name"],
    "additionalProperties": False,
}


def get_metrics_handler(
    namespace: str,
    metric_name: str,
    dimensions: Optional[List[Dict[str, str]]] = None,
    period: int = 300,
    stat: str = "Average",
    hours: int = 1,
) -> Dict[str, Any]:
    return CloudWatchClient().get_metrics(namespace, metric_name, dimensions, period, stat, hours)


# ── aws_cloudwatch_describe_alarms ───────────────────────────────────────────

ALARMS_TOOL_NAME = "aws_cloudwatch_describe_alarms"
ALARMS_TOOL_DESCRIPTION = (
    "Lists CloudWatch alarms, optionally filtered by state (OK, ALARM, INSUFFICIENT_DATA) "
    "or name prefix. Shows threshold, comparison operator, and current state reason."
)
ALARMS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "state": {
            "type": "string",
            "description": "Filter by alarm state.",
            "enum": ["OK", "ALARM", "INSUFFICIENT_DATA"],
        },
        "prefix": {"type": "string", "description": "Filter alarms whose name starts with this prefix."},
    },
    "additionalProperties": False,
}


def alarms_handler(state: Optional[str] = None, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
    return CloudWatchClient().describe_alarms(state=state, prefix=prefix)


# ── aws_cloudwatch_get_log_groups ────────────────────────────────────────────

LOG_GROUPS_TOOL_NAME = "aws_cloudwatch_get_log_groups"
LOG_GROUPS_TOOL_DESCRIPTION = (
    "Lists CloudWatch Logs log groups, optionally filtered by name prefix. "
    "Shows retention policy and stored bytes."
)
LOG_GROUPS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "prefix": {"type": "string", "description": "Filter log groups whose name starts with this prefix."},
        "limit": {"type": "integer", "description": "Max results to return (default: 50).", "default": 50},
    },
    "additionalProperties": False,
}


def log_groups_handler(prefix: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    return CloudWatchClient().get_log_groups(prefix=prefix, limit=limit)


# ── aws_cloudwatch_query_logs ────────────────────────────────────────────────

QUERY_LOGS_TOOL_NAME = "aws_cloudwatch_query_logs"
QUERY_LOGS_TOOL_DESCRIPTION = (
    "Runs a CloudWatch Logs Insights query against a log group. "
    "Supports full CloudWatch Insights query syntax (fields, filter, stats, sort, limit). "
    "Polls until complete (up to 30 seconds)."
)
QUERY_LOGS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "log_group": {"type": "string", "description": "Log group name (e.g. '/aws/lambda/my-function')."},
        "query_string": {
            "type": "string",
            "description": "CloudWatch Insights query (e.g. 'fields @timestamp, @message | filter @message like /ERROR/ | limit 20').",
        },
        "hours": {"type": "integer", "description": "Query window in hours back from now (default: 1).", "default": 1},
        "limit": {"type": "integer", "description": "Max rows to return (default: 100).", "default": 100},
    },
    "required": ["log_group", "query_string"],
    "additionalProperties": False,
}


def query_logs_handler(log_group: str, query_string: str, hours: int = 1, limit: int = 100) -> Dict[str, Any]:
    return CloudWatchClient().query_logs(log_group, query_string, hours, limit)
