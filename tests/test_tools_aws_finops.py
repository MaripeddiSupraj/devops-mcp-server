"""
tests/test_tools_aws_finops.py
-------------------------------
Unit tests for aws_find_idle_resources and aws_detect_cost_anomalies.
No real AWS calls are made — all boto3 surfaces are patched.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "error"}}, "op")


# ── IdleResourcesClient ───────────────────────────────────────────────────────

class TestIdleResourcesClient:

    def _make_client(self, mock_ec2, mock_rds, mock_cw):
        with patch("integrations.idle_resources_client._session") as ms:
            sess = MagicMock()
            sess.client.side_effect = lambda svc: {
                "ec2": mock_ec2, "rds": mock_rds, "cloudwatch": mock_cw
            }[svc]
            ms.return_value = sess
            from integrations.idle_resources_client import IdleResourcesClient
            return IdleResourcesClient(cpu_threshold=5.0, days=7)

    def test_idle_ec2_below_threshold(self):
        mock_ec2 = MagicMock()
        mock_rds = MagicMock()
        mock_cw = MagicMock()

        mock_ec2.describe_instances.return_value = {
            "Reservations": [{"Instances": [{
                "InstanceId": "i-001",
                "State": {"Name": "running"},
                "InstanceType": "t3.micro",
                "Tags": [{"Key": "Name", "Value": "dev-box"}],
                "LaunchTime": "2026-01-01",
            }]}]
        }
        mock_ec2.describe_volumes.return_value = {"Volumes": []}
        mock_rds.describe_db_instances.return_value = {"DBInstances": []}
        mock_cw.get_metric_statistics.return_value = {
            "Datapoints": [{"Average": 2.0, "Timestamp": "2026-04-28"}]
        }

        client = self._make_client(mock_ec2, mock_rds, mock_cw)
        result = client.find_all()

        assert result["summary"]["idle_ec2_instances"] == 1
        assert result["idle_ec2"][0]["instance_id"] == "i-001"
        assert result["idle_ec2"][0]["avg_cpu_pct"] == 2.0

    def test_active_ec2_above_threshold_not_flagged(self):
        mock_ec2 = MagicMock()
        mock_rds = MagicMock()
        mock_cw = MagicMock()

        mock_ec2.describe_instances.return_value = {
            "Reservations": [{"Instances": [{
                "InstanceId": "i-busy",
                "State": {"Name": "running"},
                "InstanceType": "t3.large",
                "Tags": [],
                "LaunchTime": "2026-01-01",
            }]}]
        }
        mock_ec2.describe_volumes.return_value = {"Volumes": []}
        mock_rds.describe_db_instances.return_value = {"DBInstances": []}
        mock_cw.get_metric_statistics.return_value = {
            "Datapoints": [{"Average": 75.0, "Timestamp": "2026-04-28"}]
        }

        client = self._make_client(mock_ec2, mock_rds, mock_cw)
        result = client.find_all()

        assert result["summary"]["idle_ec2_instances"] == 0
        assert result["idle_ec2"] == []

    def test_no_cloudwatch_data_flagged_as_idle(self):
        mock_ec2 = MagicMock()
        mock_rds = MagicMock()
        mock_cw = MagicMock()

        mock_ec2.describe_instances.return_value = {
            "Reservations": [{"Instances": [{
                "InstanceId": "i-ghost",
                "State": {"Name": "running"},
                "InstanceType": "t3.micro",
                "Tags": [],
                "LaunchTime": "2026-01-01",
            }]}]
        }
        mock_ec2.describe_volumes.return_value = {"Volumes": []}
        mock_rds.describe_db_instances.return_value = {"DBInstances": []}
        mock_cw.get_metric_statistics.return_value = {"Datapoints": []}

        client = self._make_client(mock_ec2, mock_rds, mock_cw)
        result = client.find_all()

        assert result["summary"]["idle_ec2_instances"] == 1
        assert result["idle_ec2"][0]["avg_cpu_pct"] is None

    def test_stopped_rds_flagged(self):
        mock_ec2 = MagicMock()
        mock_rds = MagicMock()
        mock_cw = MagicMock()

        mock_ec2.describe_instances.return_value = {"Reservations": []}
        mock_ec2.describe_volumes.return_value = {"Volumes": []}
        mock_rds.describe_db_instances.return_value = {"DBInstances": [{
            "DBInstanceIdentifier": "my-db",
            "DBInstanceStatus": "stopped",
            "Engine": "postgres",
            "DBInstanceClass": "db.t3.micro",
            "MultiAZ": False,
        }]}
        mock_cw.get_metric_statistics.return_value = {"Datapoints": []}

        client = self._make_client(mock_ec2, mock_rds, mock_cw)
        result = client.find_all()

        assert result["summary"]["idle_rds_instances"] == 1
        assert result["idle_rds"][0]["identifier"] == "my-db"
        assert result["idle_rds"][0]["reason"] == "instance is stopped"

    def test_unattached_ebs_flagged(self):
        mock_ec2 = MagicMock()
        mock_rds = MagicMock()
        mock_cw = MagicMock()

        mock_ec2.describe_instances.return_value = {"Reservations": []}
        mock_ec2.describe_volumes.return_value = {"Volumes": [{
            "VolumeId": "vol-001",
            "Size": 100,
            "VolumeType": "gp3",
            "State": "available",
            "CreateTime": "2026-01-01",
            "Tags": [{"Key": "Name", "Value": "old-data"}],
        }]}
        mock_rds.describe_db_instances.return_value = {"DBInstances": []}
        mock_cw.get_metric_statistics.return_value = {"Datapoints": []}

        client = self._make_client(mock_ec2, mock_rds, mock_cw)
        result = client.find_all()

        assert result["summary"]["unattached_ebs_volumes"] == 1
        assert result["unattached_ebs"][0]["volume_id"] == "vol-001"
        assert result["unattached_ebs"][0]["size_gb"] == 100

    def test_summary_counts_all_types(self):
        mock_ec2 = MagicMock()
        mock_rds = MagicMock()
        mock_cw = MagicMock()

        mock_ec2.describe_instances.return_value = {
            "Reservations": [{"Instances": [{
                "InstanceId": "i-001", "State": {"Name": "running"},
                "InstanceType": "t3.micro", "Tags": [], "LaunchTime": "2026-01-01",
            }]}]
        }
        mock_ec2.describe_volumes.return_value = {"Volumes": [{
            "VolumeId": "vol-001", "Size": 50, "VolumeType": "gp2",
            "State": "available", "CreateTime": "2026-01-01", "Tags": [],
        }]}
        mock_rds.describe_db_instances.return_value = {"DBInstances": [{
            "DBInstanceIdentifier": "db-1", "DBInstanceStatus": "stopped",
            "Engine": "mysql", "DBInstanceClass": "db.t3.micro", "MultiAZ": False,
        }]}
        mock_cw.get_metric_statistics.return_value = {"Datapoints": []}

        client = self._make_client(mock_ec2, mock_rds, mock_cw)
        result = client.find_all()

        assert result["summary"]["total_idle_resources"] == 3

    def test_ec2_api_error_returns_empty(self):
        mock_ec2 = MagicMock()
        mock_rds = MagicMock()
        mock_cw = MagicMock()

        mock_ec2.describe_instances.side_effect = _client_error("AccessDenied")
        mock_ec2.describe_volumes.return_value = {"Volumes": []}
        mock_rds.describe_db_instances.return_value = {"DBInstances": []}

        client = self._make_client(mock_ec2, mock_rds, mock_cw)
        result = client.find_all()

        assert result["idle_ec2"] == []

    def test_tool_handler_passthrough(self):
        with patch("integrations.idle_resources_client._session") as ms:
            sess = MagicMock()
            mock_ec2 = MagicMock()
            mock_rds = MagicMock()
            mock_cw = MagicMock()
            sess.client.side_effect = lambda svc: {
                "ec2": mock_ec2, "rds": mock_rds, "cloudwatch": mock_cw
            }[svc]
            ms.return_value = sess

            mock_ec2.describe_instances.return_value = {"Reservations": []}
            mock_ec2.describe_volumes.return_value = {"Volumes": []}
            mock_rds.describe_db_instances.return_value = {"DBInstances": []}

            from tools.aws.idle_resources import handler
            result = handler(cpu_threshold_pct=10.0, lookback_days=14)

        assert "summary" in result
        assert result["summary"]["cpu_threshold_pct"] == 10.0
        assert result["summary"]["lookback_days"] == 14


# ── CostAnomalyClient ─────────────────────────────────────────────────────────

class TestCostAnomalyClient:

    def _make_client(self, ce_mock, threshold=20.0, lookback=14):
        with patch("integrations.cost_anomaly_client._session") as ms:
            sess = MagicMock()
            sess.client.return_value = ce_mock
            ms.return_value = sess
            from integrations.cost_anomaly_client import CostAnomalyClient
            return CostAnomalyClient(threshold_pct=threshold, lookback_days=lookback)

    def _make_ce_response(self, costs: dict):
        """Build a minimal Cost Explorer response from {service: amount}."""
        groups = [
            {
                "Keys": [svc],
                "Metrics": {"UnblendedCost": {"Amount": str(amount), "Unit": "USD"}},
            }
            for svc, amount in costs.items()
        ]
        return {
            "ResultsByTime": [{
                "TimePeriod": {"Start": "2026-04-01", "End": "2026-04-15"},
                "Groups": groups,
            }]
        }

    def test_spike_above_threshold_flagged(self):
        ce = MagicMock()
        ce.get_cost_and_usage.side_effect = [
            self._make_ce_response({"Amazon EC2": 100.0}),  # current (called first)
            self._make_ce_response({"Amazon EC2": 50.0}),   # previous (called second)
        ]

        client = self._make_client(ce)
        result = client.detect()

        assert result["summary"]["anomalies_found"] == 1
        anomaly = result["anomalies"][0]
        assert anomaly["service"] == "Amazon EC2"
        assert anomaly["change_pct"] == 100.0
        assert anomaly["type"] == "spike"

    def test_below_threshold_not_flagged(self):
        ce = MagicMock()
        ce.get_cost_and_usage.side_effect = [
            self._make_ce_response({"Amazon EC2": 110.0}),  # current (called first)
            self._make_ce_response({"Amazon EC2": 100.0}),  # previous — 10% up
        ]

        client = self._make_client(ce, threshold=20.0)
        result = client.detect()

        assert result["summary"]["anomalies_found"] == 0

    def test_new_service_flagged_as_new_spend(self):
        ce = MagicMock()
        ce.get_cost_and_usage.side_effect = [
            self._make_ce_response({"AWS Lambda": 25.0}),       # current (called first)
            self._make_ce_response({}),                          # previous — nothing
        ]

        client = self._make_client(ce)
        result = client.detect()

        assert result["summary"]["anomalies_found"] == 1
        assert result["anomalies"][0]["type"] == "new_spend"
        assert result["anomalies"][0]["change_pct"] is None

    def test_new_spend_below_1_dollar_ignored(self):
        ce = MagicMock()
        ce.get_cost_and_usage.side_effect = [
            self._make_ce_response({"AWS Config": 0.05}),  # current
            self._make_ce_response({}),                     # previous
        ]

        client = self._make_client(ce)
        result = client.detect()

        assert result["summary"]["anomalies_found"] == 0

    def test_anomalies_sorted_by_dollar_increase(self):
        ce = MagicMock()
        ce.get_cost_and_usage.side_effect = [
            self._make_ce_response({"EC2": 50.0, "RDS": 30.0}),  # current
            self._make_ce_response({"EC2": 10.0, "RDS": 10.0}),  # previous
        ]

        client = self._make_client(ce)
        result = client.detect()

        assert result["anomalies"][0]["service"] == "EC2"   # $40 increase
        assert result["anomalies"][1]["service"] == "RDS"   # $20 increase

    def test_total_change_pct_in_summary(self):
        ce = MagicMock()
        ce.get_cost_and_usage.side_effect = [
            self._make_ce_response({"EC2": 150.0}),   # current (called first)
            self._make_ce_response({"EC2": 100.0}),   # previous
        ]

        client = self._make_client(ce)
        result = client.detect()

        assert result["summary"]["total_current_cost_usd"] == 150.0
        assert result["summary"]["total_previous_cost_usd"] == 100.0
        assert result["summary"]["total_change_pct"] == 50.0

    def test_all_services_current_in_result(self):
        ce = MagicMock()
        ce.get_cost_and_usage.side_effect = [
            self._make_ce_response({"EC2": 60.0, "S3": 5.0}),  # current
            self._make_ce_response({"EC2": 50.0}),               # previous
        ]

        client = self._make_client(ce)
        result = client.detect()

        service_names = [s["service"] for s in result["all_services_current"]]
        assert "EC2" in service_names
        assert "S3" in service_names

    def test_tool_handler_passthrough(self):
        with patch("integrations.cost_anomaly_client._session") as ms:
            ce = MagicMock()
            sess = MagicMock()
            sess.client.return_value = ce
            ms.return_value = sess

            ce.get_cost_and_usage.side_effect = [
                {"ResultsByTime": []},
                {"ResultsByTime": []},
            ]

            from tools.aws.cost_anomaly import handler
            result = handler(threshold_pct=30.0, lookback_days=28)

        assert result["summary"]["threshold_pct"] == 30.0
        assert result["summary"]["anomalies_found"] == 0
