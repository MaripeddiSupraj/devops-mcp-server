"""
tools/terraform/apply.py
------------------------
MCP tool definition for ``terraform_apply``.
"""

from __future__ import annotations

from typing import Any, Dict

from core.config import get_settings
from core.logger import get_logger
from integrations.terraform_runner import TerraformRunner

log = get_logger(__name__)

# ── Tool metadata ────────────────────────────────────────────────────────────

TOOL_NAME = "terraform_apply"
TOOL_DESCRIPTION = (
    "Runs `terraform apply` in the specified directory. "
    "By default requires manual approval unless auto_approve=true is passed. "
    "Use with caution in production environments."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Absolute path to the Terraform working directory.",
        },
        "auto_approve": {
            "type": "boolean",
            "description": "Skip interactive approval. Defaults to false.",
            "default": False,
        },
    },
    "required": ["path"],
    "additionalProperties": False,
}


# ── Handler ──────────────────────────────────────────────────────────────────

def handler(path: str, auto_approve: bool = False) -> Dict[str, Any]:
    """
    Execute ``terraform apply``.

    Args:
        path:         Terraform working directory.
        auto_approve: Pass ``-auto-approve`` to Terraform.

    Returns:
        Dict with ``stdout``, ``stderr``, ``exit_code``.
    """
    settings = get_settings()

    # In dry-run server mode, refuse to apply
    if settings.dry_run:
        log.warning("terraform_apply_blocked_dry_run", path=path)
        return {
            "status": "blocked",
            "reason": "Server is running in DRY_RUN mode. terraform_apply is disabled.",
            "exit_code": -1,
        }

    runner = TerraformRunner()
    result = runner.apply(path, auto_approve=auto_approve)
    result["auto_approve"] = auto_approve
    return result
