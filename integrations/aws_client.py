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

    def stop_instance(self, instance_id: str) -> Dict[str, Any]:
        """Stop a running EC2 instance (can be restarted)."""
        try:
            resp = self._ec2.stop_instances(InstanceIds=[instance_id])
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"stop_instances failed: {exc}") from exc
        state = resp["StoppingInstances"][0]
        log.info("ec2_instance_stopped", instance_id=instance_id)
        return {
            "instance_id": instance_id,
            "previous_state": state["PreviousState"]["Name"],
            "current_state": state["CurrentState"]["Name"],
        }

    def start_instance(self, instance_id: str) -> Dict[str, Any]:
        """Start a stopped EC2 instance."""
        try:
            resp = self._ec2.start_instances(InstanceIds=[instance_id])
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"start_instances failed: {exc}") from exc
        state = resp["StartingInstances"][0]
        log.info("ec2_instance_started", instance_id=instance_id)
        return {
            "instance_id": instance_id,
            "previous_state": state["PreviousState"]["Name"],
            "current_state": state["CurrentState"]["Name"],
        }

    def terminate_instance(self, instance_id: str) -> Dict[str, Any]:
        """Permanently terminate an EC2 instance (irreversible)."""
        try:
            resp = self._ec2.terminate_instances(InstanceIds=[instance_id])
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"terminate_instances failed: {exc}") from exc
        state = resp["TerminatingInstances"][0]
        log.info("ec2_instance_terminated", instance_id=instance_id)
        return {
            "instance_id": instance_id,
            "previous_state": state["PreviousState"]["Name"],
            "current_state": state["CurrentState"]["Name"],
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

    def upload_object(self, bucket: str, key: str, body: str, content_type: str = "text/plain") -> Dict[str, Any]:
        """Upload a string body as an S3 object."""
        try:
            self._s3.put_object(Bucket=bucket, Key=key, Body=body.encode(), ContentType=content_type)
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"put_object failed: {exc}") from exc
        log.info("s3_object_uploaded", bucket=bucket, key=key)
        return {"bucket": bucket, "key": key, "content_type": content_type, "size_bytes": len(body.encode())}


class CloudWatchClient:
    """CloudWatch operations used by MCP tool handlers."""

    def __init__(self) -> None:
        self._cw = _session().client("cloudwatch")
        self._logs = _session().client("logs")

    def get_metrics(
        self,
        namespace: str,
        metric_name: str,
        dimensions: Optional[List[Dict[str, str]]] = None,
        period: int = 300,
        stat: str = "Average",
        hours: int = 1,
    ) -> Dict[str, Any]:
        from datetime import datetime, timezone, timedelta
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=hours)
        kwargs: Dict[str, Any] = {
            "Namespace": namespace,
            "MetricName": metric_name,
            "StartTime": start,
            "EndTime": end,
            "Period": period,
            "Statistics": [stat],
        }
        if dimensions:
            kwargs["Dimensions"] = dimensions
        try:
            resp = self._cw.get_metric_statistics(**kwargs)
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"get_metric_statistics failed: {exc}") from exc
        datapoints = sorted(resp.get("Datapoints", []), key=lambda d: d["Timestamp"])
        return {
            "namespace": namespace,
            "metric": metric_name,
            "stat": stat,
            "period_seconds": period,
            "datapoints": [
                {"timestamp": str(d["Timestamp"]), "value": d[stat]}
                for d in datapoints
            ],
        }

    def describe_alarms(self, state: Optional[str] = None, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        kwargs: Dict[str, Any] = {}
        if state:
            kwargs["StateValue"] = state
        if prefix:
            kwargs["AlarmNamePrefix"] = prefix
        try:
            resp = self._cw.describe_alarms(**kwargs)
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"describe_alarms failed: {exc}") from exc
        return [
            {
                "name": a["AlarmName"],
                "state": a["StateValue"],
                "reason": a.get("StateReason", ""),
                "metric": a.get("MetricName"),
                "namespace": a.get("Namespace"),
                "threshold": a.get("Threshold"),
                "comparison": a.get("ComparisonOperator"),
            }
            for a in resp.get("MetricAlarms", [])
        ]

    def get_log_groups(self, prefix: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        kwargs: Dict[str, Any] = {"limit": limit}
        if prefix:
            kwargs["logGroupNamePrefix"] = prefix
        try:
            resp = self._logs.describe_log_groups(**kwargs)
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"describe_log_groups failed: {exc}") from exc
        return [
            {
                "name": g["logGroupName"],
                "retention_days": g.get("retentionInDays"),
                "stored_bytes": g.get("storedBytes", 0),
                "created": str(g.get("creationTime", "")),
            }
            for g in resp.get("logGroups", [])
        ]

    def query_logs(
        self,
        log_group: str,
        query_string: str,
        hours: int = 1,
        limit: int = 100,
    ) -> Dict[str, Any]:
        import time
        from datetime import datetime, timezone, timedelta
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=hours)
        try:
            start_resp = self._logs.start_query(
                logGroupName=log_group,
                startTime=int(start.timestamp()),
                endTime=int(end.timestamp()),
                queryString=query_string,
                limit=limit,
            )
            query_id = start_resp["queryId"]
            for _ in range(30):
                result = self._logs.get_query_results(queryId=query_id)
                if result["status"] in ("Complete", "Failed", "Cancelled"):
                    break
                time.sleep(1)
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"CloudWatch Logs query failed: {exc}") from exc
        rows = [
            {f["field"]: f["value"] for f in row}
            for row in result.get("results", [])
        ]
        return {"status": result["status"], "results": rows, "scanned_bytes": result.get("statistics", {}).get("bytesScanned")}


class SecretsClient:
    """AWS Secrets Manager operations used by MCP tool handlers."""

    def __init__(self) -> None:
        self._sm = _session().client("secretsmanager")

    def get_secret(self, secret_id: str) -> Dict[str, Any]:
        try:
            resp = self._sm.get_secret_value(SecretId=secret_id)
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"get_secret_value failed: {exc}") from exc
        log.info("secret_retrieved", secret_id=secret_id)
        return {
            "name": resp["Name"],
            "arn": resp["ARN"],
            "secret_string": resp.get("SecretString"),
            "version_id": resp.get("VersionId"),
        }

    def create_secret(self, name: str, secret_string: str, description: str = "") -> Dict[str, Any]:
        try:
            resp = self._sm.create_secret(
                Name=name,
                SecretString=secret_string,
                Description=description,
            )
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"create_secret failed: {exc}") from exc
        log.info("secret_created", name=name)
        return {"name": resp["Name"], "arn": resp["ARN"], "version_id": resp["VersionId"]}


class SSMClient:
    """AWS SSM Parameter Store operations used by MCP tool handlers."""

    def __init__(self) -> None:
        self._ssm = _session().client("ssm")

    def get_parameter(self, name: str, with_decryption: bool = True) -> Dict[str, Any]:
        try:
            resp = self._ssm.get_parameter(Name=name, WithDecryption=with_decryption)
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"get_parameter failed: {exc}") from exc
        p = resp["Parameter"]
        return {"name": p["Name"], "type": p["Type"], "value": p["Value"], "version": p["Version"]}

    def put_parameter(self, name: str, value: str, param_type: str = "String", overwrite: bool = False) -> Dict[str, Any]:
        try:
            resp = self._ssm.put_parameter(
                Name=name, Value=value, Type=param_type, Overwrite=overwrite
            )
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"put_parameter failed: {exc}") from exc
        log.info("ssm_parameter_put", name=name)
        return {"name": name, "version": resp["Version"], "tier": resp.get("Tier", "Standard")}


class NetworkingClient:
    """AWS VPC/Security Group/Route53 operations used by MCP tool handlers."""

    def __init__(self) -> None:
        self._ec2 = _session().client("ec2")
        self._r53 = _session().client("route53")

    def list_vpcs(self) -> List[Dict[str, Any]]:
        try:
            resp = self._ec2.describe_vpcs()
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"describe_vpcs failed: {exc}") from exc
        return [
            {
                "vpc_id": v["VpcId"],
                "cidr": v["CidrBlock"],
                "state": v["State"],
                "is_default": v.get("IsDefault", False),
                "name": next((t["Value"] for t in v.get("Tags", []) if t["Key"] == "Name"), ""),
            }
            for v in resp.get("Vpcs", [])
        ]

    def list_security_groups(self, vpc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        filters = []
        if vpc_id:
            filters = [{"Name": "vpc-id", "Values": [vpc_id]}]
        try:
            resp = self._ec2.describe_security_groups(Filters=filters)
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"describe_security_groups failed: {exc}") from exc
        return [
            {
                "group_id": sg["GroupId"],
                "name": sg["GroupName"],
                "description": sg.get("Description", ""),
                "vpc_id": sg.get("VpcId"),
                "inbound_rules": len(sg.get("IpPermissions", [])),
                "outbound_rules": len(sg.get("IpPermissionsEgress", [])),
            }
            for sg in resp.get("SecurityGroups", [])
        ]

    def list_hosted_zones(self) -> List[Dict[str, Any]]:
        try:
            resp = self._r53.list_hosted_zones()
        except (ClientError, BotoCoreError) as exc:
            raise AWSClientError(f"list_hosted_zones failed: {exc}") from exc
        return [
            {
                "id": z["Id"].split("/")[-1],
                "name": z["Name"],
                "private": z["Config"].get("PrivateZone", False),
                "record_count": z["ResourceRecordSetCount"],
            }
            for z in resp.get("HostedZones", [])
        ]


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
