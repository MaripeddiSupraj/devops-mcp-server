"""tools/terraform/output.py — MCP tool for ``terraform output``."""

from __future__ import annotations

from typing import Any, Dict

from integrations.terraform_runner import TerraformRunner

TOOL_NAME = "terraform_output"
TOOL_DESCRIPTION = (
    "Retrieves Terraform output values from the current state as a JSON map. "
    "Useful for fetching IP addresses, ARNs, and other values produced by apply. "
    "Requires state to exist (run apply first)."
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
    return runner.output(path)
