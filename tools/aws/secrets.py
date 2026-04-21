"""tools/aws/secrets.py — AWS Secrets Manager and SSM Parameter Store tools."""

from __future__ import annotations

from typing import Any, Dict

from integrations.aws_client import SecretsClient, SSMClient

# ── aws_secrets_get ──────────────────────────────────────────────────────────

SECRETS_GET_TOOL_NAME = "aws_secrets_get"
SECRETS_GET_TOOL_DESCRIPTION = (
    "Retrieves a secret value from AWS Secrets Manager by name or ARN. "
    "Returns the secret string, name, ARN, and version ID."
)
SECRETS_GET_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "secret_id": {"type": "string", "description": "Secret name or ARN."},
    },
    "required": ["secret_id"],
    "additionalProperties": False,
}


def secrets_get_handler(secret_id: str) -> Dict[str, Any]:
    return SecretsClient().get_secret(secret_id)


# ── aws_secrets_create ───────────────────────────────────────────────────────

SECRETS_CREATE_TOOL_NAME = "aws_secrets_create"
SECRETS_CREATE_TOOL_DESCRIPTION = (
    "Creates a new secret in AWS Secrets Manager. "
    "The secret_string can be a plain string or a JSON-encoded key/value map."
)
SECRETS_CREATE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Unique secret name."},
        "secret_string": {"type": "string", "description": "Secret value (plain string or JSON)."},
        "description": {"type": "string", "description": "Human-readable description (optional).", "default": ""},
    },
    "required": ["name", "secret_string"],
    "additionalProperties": False,
}


def secrets_create_handler(name: str, secret_string: str, description: str = "") -> Dict[str, Any]:
    return SecretsClient().create_secret(name, secret_string, description)


# ── aws_ssm_get_parameter ────────────────────────────────────────────────────

SSM_GET_TOOL_NAME = "aws_ssm_get_parameter"
SSM_GET_TOOL_DESCRIPTION = (
    "Retrieves a parameter from AWS SSM Parameter Store. "
    "SecureString parameters are decrypted automatically."
)
SSM_GET_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Parameter name or path (e.g. /myapp/db/password)."},
        "with_decryption": {
            "type": "boolean",
            "description": "Decrypt SecureString values (default: true).",
            "default": True,
        },
    },
    "required": ["name"],
    "additionalProperties": False,
}


def ssm_get_handler(name: str, with_decryption: bool = True) -> Dict[str, Any]:
    return SSMClient().get_parameter(name, with_decryption)


# ── aws_ssm_put_parameter ────────────────────────────────────────────────────

SSM_PUT_TOOL_NAME = "aws_ssm_put_parameter"
SSM_PUT_TOOL_DESCRIPTION = (
    "Creates or updates a parameter in AWS SSM Parameter Store. "
    "Use type='SecureString' for sensitive values."
)
SSM_PUT_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Parameter name or path."},
        "value": {"type": "string", "description": "Parameter value."},
        "param_type": {
            "type": "string",
            "description": "Parameter type.",
            "enum": ["String", "StringList", "SecureString"],
            "default": "String",
        },
        "overwrite": {
            "type": "boolean",
            "description": "Overwrite if the parameter already exists (default: false).",
            "default": False,
        },
    },
    "required": ["name", "value"],
    "additionalProperties": False,
}


def ssm_put_handler(name: str, value: str, param_type: str = "String", overwrite: bool = False) -> Dict[str, Any]:
    return SSMClient().put_parameter(name, value, param_type, overwrite)
