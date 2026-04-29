"""
integrations/cost_anomaly_client.py
-------------------------------------
Detects AWS cost anomalies by comparing current period spend vs previous period
per service using Cost Explorer.

Logic:
  - Splits the lookback window into two equal halves (current vs previous)
  - Flags services where cost increased by more than `threshold_pct`
  - Also flags services that are new (appeared in current but not previous)
  - Returns anomalies sorted by absolute cost increase descending
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from core.auth import get_aws_credentials
from core.logger import get_logger

log = get_logger(__name__)


def _session() -> boto3.Session:
    key_id, secret, region = get_aws_credentials()
    return boto3.Session(
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
        region_name=region,
    )


class CostAnomalyClient:
    """
    Compares AWS spend this period vs last period per service
    and returns services that spiked beyond the threshold.
    """

    def __init__(self, threshold_pct: float = 20.0, lookback_days: int = 14) -> None:
        self._threshold_pct = threshold_pct
        self._lookback_days = lookback_days
        self._ce = _session().client("ce", region_name="us-east-1")

    def detect(self) -> Dict[str, Any]:
        today = date.today()
        half = self._lookback_days // 2

        # current period: last `half` days
        current_start = today - timedelta(days=half)
        current_end = today

        # previous period: the `half` days before that
        prev_start = today - timedelta(days=self._lookback_days)
        prev_end = current_start

        current_costs = self._get_costs(str(current_start), str(current_end))
        prev_costs = self._get_costs(str(prev_start), str(prev_end))

        anomalies = self._compare(current_costs, prev_costs)

        total_current = sum(current_costs.values())
        total_prev = sum(prev_costs.values())
        total_change_pct = (
            round(((total_current - total_prev) / total_prev) * 100, 1)
            if total_prev > 0
            else None
        )

        log.info(
            "cost_anomaly_detection_complete",
            anomalies_found=len(anomalies),
            current_total=round(total_current, 2),
            prev_total=round(total_prev, 2),
        )

        return {
            "summary": {
                "current_period": f"{current_start} to {current_end}",
                "previous_period": f"{prev_start} to {prev_end}",
                "threshold_pct": self._threshold_pct,
                "total_current_cost_usd": round(total_current, 2),
                "total_previous_cost_usd": round(total_prev, 2),
                "total_change_pct": total_change_pct,
                "anomalies_found": len(anomalies),
            },
            "anomalies": anomalies,
            "all_services_current": [
                {"service": k, "cost_usd": round(v, 4)}
                for k, v in sorted(current_costs.items(), key=lambda x: x[1], reverse=True)
            ],
        }

    # ── private ───────────────────────────────────────────────────────────────

    def _get_costs(self, start: str, end: str) -> Dict[str, float]:
        try:
            resp = self._ce.get_cost_and_usage(
                TimePeriod={"Start": start, "End": end},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
        except (ClientError, BotoCoreError) as exc:
            raise RuntimeError(f"Cost Explorer get_cost_and_usage failed: {exc}") from exc

        costs: Dict[str, float] = {}
        for period in resp.get("ResultsByTime", []):
            for group in period.get("Groups", []):
                service = group["Keys"][0]
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                costs[service] = costs.get(service, 0.0) + amount

        return costs

    def _compare(
        self,
        current: Dict[str, float],
        previous: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        anomalies = []

        for service, current_cost in current.items():
            if current_cost < 0.01:
                continue

            prev_cost = previous.get(service, 0.0)

            if prev_cost == 0.0:
                if current_cost >= 1.0:
                    anomalies.append({
                        "service": service,
                        "previous_cost_usd": 0.0,
                        "current_cost_usd": round(current_cost, 4),
                        "change_usd": round(current_cost, 4),
                        "change_pct": None,
                        "type": "new_spend",
                        "reason": f"New spend detected: ${round(current_cost, 2)} (was $0)",
                    })
                continue

            change_pct = ((current_cost - prev_cost) / prev_cost) * 100

            if change_pct >= self._threshold_pct:
                anomalies.append({
                    "service": service,
                    "previous_cost_usd": round(prev_cost, 4),
                    "current_cost_usd": round(current_cost, 4),
                    "change_usd": round(current_cost - prev_cost, 4),
                    "change_pct": round(change_pct, 1),
                    "type": "spike",
                    "reason": f"Cost increased {round(change_pct, 1)}% (${round(prev_cost, 2)} → ${round(current_cost, 2)})",
                })

        anomalies.sort(key=lambda x: x["change_usd"], reverse=True)
        return anomalies
