"""tools/aws/cost_anomaly.py — Detect AWS cost anomalies vs previous period."""

from __future__ import annotations

from typing import Any, Dict

from integrations.cost_anomaly_client import CostAnomalyClient

TOOL_NAME = "aws_detect_cost_anomalies"
TOOL_DESCRIPTION = (
    "Compares AWS spend this period vs the previous period per service "
    "and flags services whose cost spiked beyond the threshold. "
    "Also highlights new services that had no spend in the previous period. "
    "Returns anomalies sorted by cost increase, plus a full breakdown of current spend. "
    "Requires AWS Cost Explorer access (us-east-1)."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "threshold_pct": {
            "type": "number",
            "description": "Percentage increase that triggers an anomaly flag (default: 20).",
            "default": 20.0,
        },
        "lookback_days": {
            "type": "integer",
            "description": (
                "Total days to analyse. Split evenly: first half = previous period, "
                "second half = current period (default: 14 → 7 days each)."
            ),
            "default": 14,
        },
    },
    "additionalProperties": False,
}


def handler(
    threshold_pct: float = 20.0,
    lookback_days: int = 14,
) -> Dict[str, Any]:
    """
    Detect cost anomalies by comparing current vs previous period per service.

    Returns:
        Dict with ``summary``, ``anomalies``, ``all_services_current``.
    """
    client = CostAnomalyClient(threshold_pct=threshold_pct, lookback_days=lookback_days)
    return client.detect()
