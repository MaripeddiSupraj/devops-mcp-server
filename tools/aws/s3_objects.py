"""tools/aws/s3_objects.py — S3 object operations."""

from __future__ import annotations

from typing import Any, Dict

from integrations.aws_client import S3Client

TOOL_NAME = "aws_s3_upload_object"
TOOL_DESCRIPTION = (
    "Uploads a text string as an object to an S3 bucket. "
    "Useful for storing configs, logs, or small artifacts. "
    "The bucket must already exist."
)
TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "bucket": {"type": "string", "description": "Target S3 bucket name."},
        "key": {"type": "string", "description": "Object key (path within the bucket, e.g. 'configs/app.json')."},
        "body": {"type": "string", "description": "String content to upload."},
        "content_type": {
            "type": "string",
            "description": "MIME type (default: text/plain).",
            "default": "text/plain",
        },
    },
    "required": ["bucket", "key", "body"],
    "additionalProperties": False,
}


def handler(bucket: str, key: str, body: str, content_type: str = "text/plain") -> Dict[str, Any]:
    return S3Client().upload_object(bucket, key, body, content_type)
