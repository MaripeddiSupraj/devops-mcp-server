"""
tools/terraform/plan.py
-----------------------
MCP tool definition for ``terraform_plan``.
"""

from __future__ import annotations

from typing import Any, Dict

from core.config import get_settings
from core.logger import get_logger
from integrations.terraform_runner import TerraformRunner

log = get_logger(__name__)

# ── Tool metadata ────────────────────────────────────────────────────────────

TOOL_NAME = "terraform_plan"
TOOL_DESCRIPTION = (
    "Runs `terraform plan` in the specified directory. "
    "Returns stdout, stderr, and exit code. "
    "Exit code 0 = no changes, 2 = changes present, non-zero = error."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Absolute path to the Terraform working directory.",
        },
        "dry_run": {
            "type": "boolean",
            "description": "If true, only validates the configuration without contacting providers.",
            "default": False,
        },
    },
    "required": ["path"],
    "additionalProperties": False,
}


# ── Handler ──────────────────────────────────────────────────────────────────

def handler(path: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Execute ``terraform plan`` and return structured output.

    Args:
        path:    Terraform working directory (must be under TERRAFORM_ALLOWED_BASE_DIR).
        dry_run: When True, appends ``-validate`` instead of running a real plan.

    Returns:
        Dict with ``stdout``, ``stderr``, ``exit_code``, and ``has_changes``.
    """
    settings = get_settings()

    # Global dry-run override from server config
    effective_dry_run = dry_run or settings.dry_run

    runner = TerraformRunner()

    if effective_dry_run:
        log.info("terraform_plan_dry_run", path=path)
        result = runner._run(["validate", "-no-color"], runner._validated_path(path))
    else:
        result = runner.plan(path)

    result["has_changes"] = result["exit_code"] == 2
    result["dry_run"] = effective_dry_run
    return result
