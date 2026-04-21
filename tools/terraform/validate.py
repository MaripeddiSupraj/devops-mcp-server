"""tools/terraform/validate.py — MCP tool for ``terraform validate``."""

from __future__ import annotations

from typing import Any, Dict

from integrations.terraform_runner import TerraformRunner

TOOL_NAME = "terraform_validate"
TOOL_DESCRIPTION = (
    "Validates Terraform configuration syntax and internal consistency. "
    "Does not contact any provider APIs — safe to run without credentials. "
    "Returns exit_code 0 on success."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Absolute path to the Terraform working directory.",
        },
    },
    "required": ["path"],
    "additionalProperties": False,
}


def handler(path: str) -> Dict[str, Any]:
    runner = TerraformRunner()
    result = runner.validate(path)
    result["valid"] = result["exit_code"] == 0
    return result
