"""
tools/terraform/destroy.py
--------------------------
MCP tool definition for ``terraform_destroy``.

Extra safety: destroy is only allowed when both ``auto_approve=true``
AND the ``confirm_destroy`` field equals the exact string ``"DESTROY"``.
"""

from __future__ import annotations

from typing import Any, Dict

from core.config import get_settings
from core.logger import get_logger
from integrations.terraform_runner import TerraformRunner

log = get_logger(__name__)

TOOL_NAME = "terraform_destroy"
TOOL_DESCRIPTION = (
    "Runs `terraform destroy` in the specified directory. "
    "DESTRUCTIVE — permanently removes all resources managed by the configuration. "
    "Requires confirm_destroy='DESTROY' to proceed."
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
            "description": "Skip interactive approval.",
            "default": False,
        },
        "confirm_destroy": {
            "type": "string",
            "description": "Must be the exact string 'DESTROY' to confirm the operation.",
        },
    },
    "required": ["path", "confirm_destroy"],
    "additionalProperties": False,
}


def handler(path: str, confirm_destroy: str, auto_approve: bool = False) -> Dict[str, Any]:
    """
    Execute ``terraform destroy``.

    Args:
        path:             Terraform working directory.
        confirm_destroy:  Must equal ``"DESTROY"`` — explicit safety gate.
        auto_approve:     Pass ``-auto-approve`` to Terraform.
    """
    if confirm_destroy != "DESTROY":
        return {
            "stdout": "",
            "stderr": "Destroy confirmation failed. Pass confirm_destroy='DESTROY' to proceed.",
            "exit_code": -1,
            "blocked": True,
        }

    if get_settings().dry_run:
        return {
            "stdout": "",
            "stderr": "Server is in DRY_RUN mode. terraform_destroy is disabled.",
            "exit_code": -1,
            "blocked": True,
        }

    log.warning("terraform_destroy_executing", path=path)
    runner = TerraformRunner()
    result = runner.destroy(path, auto_approve=auto_approve)
    result["auto_approve"] = auto_approve
    return result
