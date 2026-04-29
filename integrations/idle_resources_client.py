"""
integrations/idle_resources_client.py
--------------------------------------
Detects idle/wasted AWS resources by querying EC2, RDS, and EBS via CloudWatch
and the EC2/RDS APIs.

Idle thresholds (all configurable via constructor):
  EC2:  avg CPU < cpu_threshold% over the last `days` days
  RDS:  stopped instances (status != 'available') or avg CPU < cpu_threshold%
  EBS:  volumes in 'available' state (unattached)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from core.auth import get_aws_credentials
from core.logger import get_logger

log = get_logger(__name__)


def _session() -> boto3.Session:
    key_id, secret, region = get_aws_credentials()
    return boto3.Session(
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
        region_name=region,
    )


class IdleResourcesClient:
    """Finds idle EC2 instances, stopped/idle RDS instances, and unattached EBS volumes."""

    def __init__(self, cpu_threshold: float = 5.0, days: int = 7) -> None:
        self._cpu_threshold = cpu_threshold
        self._days = days
        sess = _session()
        self._ec2 = sess.client("ec2")
        self._rds = sess.client("rds")
        self._cw = sess.client("cloudwatch")

    # ── public ────────────────────────────────────────────────────────────────

    def find_all(self) -> Dict[str, Any]:
        idle_ec2 = self._idle_ec2_instances()
        idle_rds = self._idle_rds_instances()
        unattached_ebs = self._unattached_ebs_volumes()

        total_count = len(idle_ec2) + len(idle_rds) + len(unattached_ebs)

        return {
            "summary": {
                "total_idle_resources": total_count,
                "idle_ec2_instances": len(idle_ec2),
                "idle_rds_instances": len(idle_rds),
                "unattached_ebs_volumes": len(unattached_ebs),
                "cpu_threshold_pct": self._cpu_threshold,
                "lookback_days": self._days,
            },
            "idle_ec2": idle_ec2,
            "idle_rds": idle_rds,
            "unattached_ebs": unattached_ebs,
        }

    # ── EC2 ───────────────────────────────────────────────────────────────────

    def _idle_ec2_instances(self) -> List[Dict[str, Any]]:
        try:
            resp = self._ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            )
        except (ClientError, BotoCoreError) as exc:
            log.error("idle_ec2_describe_failed", error=str(exc))
            return []

        instances = []
        for reservation in resp.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                instances.append(inst)

        idle = []
        for inst in instances:
            instance_id = inst["InstanceId"]
            avg_cpu = self._get_avg_cpu_ec2(instance_id)
            if avg_cpu is None or avg_cpu < self._cpu_threshold:
                name = next(
                    (t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), ""
                )
                idle.append({
                    "instance_id": instance_id,
                    "name": name,
                    "instance_type": inst.get("InstanceType"),
                    "state": inst["State"]["Name"],
                    "avg_cpu_pct": round(avg_cpu, 2) if avg_cpu is not None else None,
                    "lookback_days": self._days,
                    "reason": f"avg CPU {round(avg_cpu, 2)}% < {self._cpu_threshold}% over {self._days}d"
                    if avg_cpu is not None
                    else f"no CPU data for {self._days}d",
                    "launch_time": str(inst.get("LaunchTime", "")),
                })
        log.info("idle_ec2_found", count=len(idle))
        return idle

    def _get_avg_cpu_ec2(self, instance_id: str) -> Optional[float]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=self._days)
        try:
            resp = self._cw.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start,
                EndTime=end,
                Period=int(timedelta(days=self._days).total_seconds()),
                Statistics=["Average"],
            )
        except (ClientError, BotoCoreError):
            return None
        datapoints = resp.get("Datapoints", [])
        if not datapoints:
            return None
        return sum(d["Average"] for d in datapoints) / len(datapoints)

    # ── RDS ───────────────────────────────────────────────────────────────────

    def _idle_rds_instances(self) -> List[Dict[str, Any]]:
        try:
            resp = self._rds.describe_db_instances()
        except (ClientError, BotoCoreError) as exc:
            log.error("idle_rds_describe_failed", error=str(exc))
            return []

        idle = []
        for db in resp.get("DBInstances", []):
            identifier = db["DBInstanceIdentifier"]
            status = db.get("DBInstanceStatus", "")

            if status == "stopped":
                idle.append({
                    "identifier": identifier,
                    "engine": db.get("Engine"),
                    "instance_class": db.get("DBInstanceClass"),
                    "status": status,
                    "avg_cpu_pct": None,
                    "reason": "instance is stopped",
                    "multi_az": db.get("MultiAZ", False),
                })
                continue

            if status == "available":
                avg_cpu = self._get_avg_cpu_rds(identifier)
                if avg_cpu is not None and avg_cpu < self._cpu_threshold:
                    idle.append({
                        "identifier": identifier,
                        "engine": db.get("Engine"),
                        "instance_class": db.get("DBInstanceClass"),
                        "status": status,
                        "avg_cpu_pct": round(avg_cpu, 2),
                        "reason": f"avg CPU {round(avg_cpu, 2)}% < {self._cpu_threshold}% over {self._days}d",
                        "multi_az": db.get("MultiAZ", False),
                    })

        log.info("idle_rds_found", count=len(idle))
        return idle

    def _get_avg_cpu_rds(self, identifier: str) -> Optional[float]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=self._days)
        try:
            resp = self._cw.get_metric_statistics(
                Namespace="AWS/RDS",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "DBInstanceIdentifier", "Value": identifier}],
                StartTime=start,
                EndTime=end,
                Period=int(timedelta(days=self._days).total_seconds()),
                Statistics=["Average"],
            )
        except (ClientError, BotoCoreError):
            return None
        datapoints = resp.get("Datapoints", [])
        if not datapoints:
            return None
        return sum(d["Average"] for d in datapoints) / len(datapoints)

    # ── EBS ───────────────────────────────────────────────────────────────────

    def _unattached_ebs_volumes(self) -> List[Dict[str, Any]]:
        try:
            resp = self._ec2.describe_volumes(
                Filters=[{"Name": "status", "Values": ["available"]}]
            )
        except (ClientError, BotoCoreError) as exc:
            log.error("idle_ebs_describe_failed", error=str(exc))
            return []

        volumes = []
        for vol in resp.get("Volumes", []):
            name = next(
                (t["Value"] for t in vol.get("Tags", []) if t["Key"] == "Name"), ""
            )
            volumes.append({
                "volume_id": vol["VolumeId"],
                "name": name,
                "size_gb": vol.get("Size"),
                "volume_type": vol.get("VolumeType"),
                "state": vol.get("State"),
                "created": str(vol.get("CreateTime", "")),
                "reason": "unattached (no EC2 instance)",
            })

        log.info("unattached_ebs_found", count=len(volumes))
        return volumes
