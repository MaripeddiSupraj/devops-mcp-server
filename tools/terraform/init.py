"""tools/terraform/init.py — MCP tool for ``terraform init``."""

from __future__ import annotations

from typing import Any, Dict

from integrations.terraform_runner import TerraformRunner

TOOL_NAME = "terraform_init"
TOOL_DESCRIPTION = (
    "Initialises a Terraform working directory: downloads providers and modules. "
    "Must be run before plan/apply on a fresh workspace. "
    "Set upgrade=true to upgrade locked provider versions."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Absolute path to the Terraform working directory.",
        },
        "upgrade": {
            "type": "boolean",
            "description": "Pass -upgrade to update provider/module lock file.",
            "default": False,
        },
    },
    "required": ["path"],
    "additionalProperties": False,
}


def handler(path: str, upgrade: bool = False) -> Dict[str, Any]:
    runner = TerraformRunner()
    result = runner.init(path, upgrade=upgrade)
    result["initialised"] = result["exit_code"] == 0
    return result
