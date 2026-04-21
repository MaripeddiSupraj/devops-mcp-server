"""tools/aws/cost.py — AWS Cost Explorer tools."""

from __future__ import annotations

from typing import Any, Dict, List

from integrations.aws_client import CostExplorerClient

# ── aws_cost_by_service ───────────────────────────────────────────────────────

COST_BY_SERVICE_TOOL_NAME = "aws_cost_by_service"
COST_BY_SERVICE_TOOL_DESCRIPTION = (
    "Returns AWS spend broken down by service for a date range. "
    "Dates must be in YYYY-MM-DD format. Results sorted by cost descending. "
    "Note: Cost Explorer has a ~24h data lag."
)
COST_BY_SERVICE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "start": {"type": "string", "description": "Start date in YYYY-MM-DD format (e.g. '2026-03-01')."},
        "end": {"type": "string", "description": "End date in YYYY-MM-DD format (exclusive, e.g. '2026-04-01')."},
    },
    "required": ["start", "end"],
    "additionalProperties": False,
}


def cost_by_service_handler(start: str, end: str) -> List[Dict[str, Any]]:
    return CostExplorerClient().get_cost_by_service(start, end)


# ── aws_cost_monthly_total ────────────────────────────────────────────────────

MONTHLY_TOTAL_TOOL_NAME = "aws_cost_monthly_total"
MONTHLY_TOTAL_TOOL_DESCRIPTION = (
    "Returns the total AWS spend per calendar month for a date range. "
    "Useful for month-over-month cost tracking and budget reviews."
)
MONTHLY_TOTAL_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "start": {"type": "string", "description": "Start date in YYYY-MM-DD format (e.g. '2026-01-01')."},
        "end": {"type": "string", "description": "End date in YYYY-MM-DD format (e.g. '2026-04-01')."},
    },
    "required": ["start", "end"],
    "additionalProperties": False,
}


def monthly_total_handler(start: str, end: str) -> Dict[str, Any]:
    return CostExplorerClient().get_monthly_total(start, end)
