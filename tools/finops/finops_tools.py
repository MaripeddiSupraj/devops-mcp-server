"""tools/finops/finops_tools.py — Multi-cloud cost and FinOps tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ── azure_cost_by_service ─────────────────────────────────────────────────────

AZURE_COST_TOOL_NAME = "azure_cost_by_service"
AZURE_COST_TOOL_DESCRIPTION = (
    "Get Azure spend breakdown by service for a date range using Azure Cost Management. "
    "Requires AZURE_SUBSCRIPTION_ID and Azure credentials."
)
AZURE_COST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format."},
        "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format."},
    },
    "required": ["start_date", "end_date"],
    "additionalProperties": False,
}


def azure_cost_handler(start_date: str, end_date: str) -> Dict:
    from integrations.azure_client import AzureCostClient
    return AzureCostClient().get_cost_by_service(start_date, end_date)


# ── gcp_billing_monthly_spend ──────────────────────────────────────────────────

GCP_BILLING_TOOL_NAME = "gcp_billing_monthly_spend"
GCP_BILLING_TOOL_DESCRIPTION = (
    "Get GCP monthly spend breakdown by service using BigQuery billing export. "
    "Requires GCP_PROJECT_ID and a BigQuery billing export table."
)
GCP_BILLING_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "dataset": {"type": "string", "description": "BigQuery dataset containing the billing export table."},
        "table": {"type": "string", "description": "BigQuery table name (e.g. 'gcp_billing_export_v1_XXXXXX')."},
    },
    "required": ["dataset", "table"],
    "additionalProperties": False,
}


def gcp_billing_handler(dataset: str, table: str) -> Dict:
    from integrations.gcp_client import GCPBillingClient
    return GCPBillingClient().get_monthly_spend(dataset, table)


# ── infracost_estimate ────────────────────────────────────────────────────────

INFRACOST_TOOL_NAME = "infracost_estimate"
INFRACOST_TOOL_DESCRIPTION = (
    "Estimate the monthly cost of a Terraform plan using Infracost. "
    "Returns cost breakdown by resource. Requires infracost binary on PATH and INFRACOST_API_KEY."
)
INFRACOST_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Path to Terraform directory or plan JSON file."},
    },
    "required": ["path"],
    "additionalProperties": False,
}


def infracost_handler(path: str) -> Dict:
    import json
    import subprocess
    from core.config import get_settings
    cfg = get_settings()
    cmd = [cfg.infracost_binary, "breakdown", "--path", path, "--format", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"path": path, "raw": result.stdout}
    projects = data.get("projects", [])
    summary = []
    for p in projects:
        breakdown = p.get("breakdown", {})
        summary.append({
            "project": p.get("name"),
            "monthly_cost": breakdown.get("totalMonthlyCost"),
            "resources": [
                {
                    "name": r.get("name"),
                    "monthly_cost": r.get("monthlyCost"),
                }
                for r in breakdown.get("resources", [])[:20]
            ],
        })
    return {"path": path, "summary": summary, "total_monthly_cost": data.get("totalMonthlyCost")}
