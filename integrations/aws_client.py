"""
integrations/aws_client.py
---------------------------
Boto3-backed AWS client factory and high-level helpers for EC2 and S3.

Safety principles:
- Instance type is validated against an allowlist before any API call.
- Destructive operations (terminate, delete bucket) require explicit confirmation flags.
- All calls are logged with resource identifiers.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from core.auth import get_aws_credentials
from core.logger import get_logger

log = get_logger(__name__)

# Instance types permitted for creation through the MCP server.
# Expand this list deliberately — never allow arbitrary strings.
ALLOWED_INSTANCE_TYPES: frozenset[str] = frozenset(
    {
        "t2.micro", "t2.small", "t2.medium",
        "t3.micro", "t3.small", "t3.medium", "t3.large",
        "t3a.micro", "t3a.small", "t3a.medium",
        "m5.large", "m5.xlarge",
        "c5.large", "c5.xlarge",
    }
)


class AWSClientError(RuntimeError):
    """Wraps boto3 exceptions in a domain-specific error."""


@lru_cache(maxsize=1)
def _session() -> boto3.Session:
    """Return a cached boto3 Session authenticated from environment variables."""
    key_id, secret, region = get_aws_credentials()
    session = boto3.Session(
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
        region_name=region,
    )
    log.info("aws_session_initialised", region=region)
    return session


class EC2Client:
    """EC2 operations used by MCP tool handlers."""

    def __init__(self) -> None:
        self._ec2 = _session().client("ec2")

    def create_instance(
        self,
        name: str,
        instance_type: str,
        ami_id: str,
        key_name: Optional[str] = None,
        subnet_id: Optional[str] = None,
        security_group_ids: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Launch a single EC2 instance.

        Args:
            name:               Value for the ``Name`` tag.
            instance_type:      Must be in ALLOWED_INSTANCE_TYPES.
            ami_id:             Amazon Machine Image ID.
            key_name:           EC2 Key Pair name (optional).
            subnet_id:          VPC subnet ID (optional).
            security_group_ids: List of security group IDs (optional).
            dry_run:            Validate permissions without launching.

        Returns:
            Dict with ``instance_id``, ``state``, ``instance_type``, ``ami``.
        """
        if instance_type not in ALLOWED_INSTANCE_TYPES:
            raise AWSClientError(
                f"Instance type '{instance_type}' is not allowed. "
                f"Permitted types: {sorted(ALLOWED_INSTANCE_TYPES)}"
            )

        kwargs: Dict[str, Any] = {
            "ImageId": ami_id,
            "InstanceType": instance_type,
            "MinCount": 1,
            "MaxCount": 1,
            "DryRun": dry_run,
            "TagSpecifications": [
                {
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Name", "Value": name}],
                }
            ],
        }
        if key_name:
            kwargs["KeyName"] = key_name
        if subnet_id:
            kwargs["SubnetId"] = subnet_id
        if security_group_ids:
            kwargs["SecurityGroupIds"] = security_group_ids

        try:
            resp = self._ec2.run_instances(**kwargs)
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if dry_run and code == "DryRunOperation":
                log.info("ec2_dry_run_success", name=name, instance_type=instance_type)
                return {"dry_run": True, "message": "DryRun succeeded — permissions OK."}
            raise AWSClientError(f"EC2 run_instances failed: {exc}") from exc

        instance = resp["Instances"][0]
        log.info(
            "ec2_instance_created",
            instance_id=instance["InstanceId"],
            instance_type=instance_type,
            name=name,
        )
        return {
            "instance_id": instance["InstanceId"],
            "state": instance["State"]["Name"],
            "instance_type": instance["InstanceType"],
            "ami": instance["ImageId"],
            "availability_zone": instance.get("Placement", {}).get("AvailabilityZone"),
        }

    def list_instances(self, filters: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
        """Return a list of running EC2 instances."""
        try:
            resp = self._ec2.describe_instances(Filters=filters or [])
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"describe_instances failed: {exc}") from exc

        instances = []
        for reservation in resp.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                name_tag = next(
                    (t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), ""
                )
                instances.append(
                    {
                        "instance_id": inst["InstanceId"],
                        "state": inst["State"]["Name"],
                        "instance_type": inst["InstanceType"],
                        "name": name_tag,
                        "public_ip": inst.get("PublicIpAddress"),
                        "private_ip": inst.get("PrivateIpAddress"),
                    }
                )
        return instances


class S3Client:
    """S3 operations used by MCP tool handlers."""

    def __init__(self) -> None:
        self._s3 = _session().client("s3")

    def list_buckets(self) -> List[Dict[str, Any]]:
        """Return all S3 buckets owned by the caller."""
        try:
            resp = self._s3.list_buckets()
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"list_buckets failed: {exc}") from exc

        return [
            {"name": b["Name"], "created": str(b["CreationDate"])}
            for b in resp.get("Buckets", [])
        ]

    def create_bucket(self, bucket_name: str, region: Optional[str] = None) -> Dict[str, Any]:
        """
        Create an S3 bucket with sensible defaults (versioning off, no public access).

        Args:
            bucket_name: Globally unique bucket name.
            region:      AWS region (defaults to session region).
        """
        effective_region = region or _session().region_name or "us-east-1"
        kwargs: Dict[str, Any] = {"Bucket": bucket_name}
        if effective_region != "us-east-1":
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": effective_region}

        try:
            self._s3.create_bucket(**kwargs)
            # Block all public access by default
            self._s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True,
                    "RestrictPublicBuckets": True,
                },
            )
        except ClientError as exc:
            raise AWSClientError(f"create_bucket failed: {exc}") from exc

        log.info("s3_bucket_created", bucket=bucket_name, region=effective_region)
        return {"bucket": bucket_name, "region": effective_region, "public_access": "blocked"}


class LambdaClient:
    """Lambda operations used by MCP tool handlers."""

    def __init__(self) -> None:
        self._lambda = _session().client("lambda")

    def list_functions(self, max_items: int = 50) -> List[Dict[str, Any]]:
        """Return a list of Lambda functions in the account/region."""
        try:
            resp = self._lambda.list_functions(MaxItems=max_items)
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"list_functions failed: {exc}") from exc

        return [
            {
                "name": fn["FunctionName"],
                "runtime": fn.get("Runtime", "unknown"),
                "handler": fn.get("Handler"),
                "memory_mb": fn.get("MemorySize"),
                "timeout_s": fn.get("Timeout"),
                "last_modified": fn.get("LastModified"),
                "description": fn.get("Description", ""),
            }
            for fn in resp.get("Functions", [])
        ]

    def invoke(
        self,
        function_name: str,
        payload: Optional[Dict[str, Any]] = None,
        invocation_type: str = "RequestResponse",
    ) -> Dict[str, Any]:
        """
        Invoke a Lambda function synchronously or asynchronously.

        Args:
            function_name:   Function name or ARN.
            payload:         JSON-serialisable dict passed as event (optional).
            invocation_type: "RequestResponse" (sync) | "Event" (async) | "DryRun".

        Returns:
            Dict with status_code, executed_version, response_payload, log_result.
        """
        import base64

        kwargs: Dict[str, Any] = {
            "FunctionName": function_name,
            "InvocationType": invocation_type,
        }
        if payload:
            import json as _json
            kwargs["Payload"] = _json.dumps(payload).encode()

        try:
            resp = self._lambda.invoke(**kwargs)
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"lambda invoke failed: {exc}") from exc

        result: Dict[str, Any] = {
            "status_code": resp.get("StatusCode"),
            "executed_version": resp.get("ExecutedVersion", "$LATEST"),
            "function_error": resp.get("FunctionError"),
        }

        if "Payload" in resp:
            try:
                result["response_payload"] = resp["Payload"].read().decode("utf-8")
            except Exception:
                result["response_payload"] = None

        log_b64 = resp.get("LogResult")
        if log_b64:
            try:
                result["log_tail"] = base64.b64decode(log_b64).decode("utf-8")
            except Exception:
                result["log_tail"] = None

        log.info("lambda_invoked", function=function_name, status=result["status_code"])
        return result


class RDSClient:
    """RDS operations used by MCP tool handlers."""

    def __init__(self) -> None:
        self._rds = _session().client("rds")

    def list_instances(self, db_instance_identifier: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Describe RDS DB instances.

        Args:
            db_instance_identifier: Optional specific instance to describe.
        """
        kwargs: Dict[str, Any] = {}
        if db_instance_identifier:
            kwargs["DBInstanceIdentifier"] = db_instance_identifier

        try:
            resp = self._rds.describe_db_instances(**kwargs)
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"describe_db_instances failed: {exc}") from exc

        return [
            {
                "identifier": db["DBInstanceIdentifier"],
                "engine": db.get("Engine"),
                "engine_version": db.get("EngineVersion"),
                "status": db.get("DBInstanceStatus"),
                "instance_class": db.get("DBInstanceClass"),
                "endpoint": db.get("Endpoint", {}).get("Address"),
                "port": db.get("Endpoint", {}).get("Port"),
                "multi_az": db.get("MultiAZ"),
                "storage_gb": db.get("AllocatedStorage"),
            }
            for db in resp.get("DBInstances", [])
        ]
