"""tools/terraform/state_list.py — MCP tool for ``terraform state list``."""

from __future__ import annotations

from typing import Any, Dict

from integrations.terraform_runner import TerraformRunner

TOOL_NAME = "terraform_state_list"
TOOL_DESCRIPTION = (
    "Lists all resource addresses tracked in the Terraform state file. "
    "Useful for inspecting what is currently managed without running a full plan."
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
    return runner.state_list(path)
