"""
tests/test_tools_aws.py
------------------------
Unit tests for AWS tool handlers (EC2 + S3) using mocked boto3.

No real AWS calls are made. All external API surfaces are patched at
the integration layer so the tool handler logic is fully exercised.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from botocore.exceptions import ClientError


# ── Helpers ───────────────────────────────────────────────────────────────────

def _client_error(code: str, message: str = "error") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": message}}, "operation")


def _mock_ec2_client():
    return MagicMock()


# ── EC2 create_instance ───────────────────────────────────────────────────────

class TestEC2CreateInstance:
    @patch("integrations.aws_client._session")
    def test_create_instance_success(self, mock_session):
        mock_ec2 = MagicMock()
        mock_session.return_value.client.return_value = mock_ec2
        mock_ec2.run_instances.return_value = {
            "Instances": [{
                "InstanceId": "i-0abc123def456",
                "State": {"Name": "pending"},
                "InstanceType": "t3.micro",
                "ImageId": "ami-0c55b159cbfafe1f0",
                "Placement": {"AvailabilityZone": "us-east-1a"},
            }]
        }
        from integrations.aws_client import EC2Client
        # Clear lru_cache so mock is used
        from integrations.aws_client import _session
        _session.cache_clear()

        with patch("integrations.aws_client._session") as ms:
            ms.return_value.client.return_value = mock_ec2
            client = EC2Client()
            result = client.create_instance(
                name="test-server",
                instance_type="t3.micro",
                ami_id="ami-0c55b159cbfafe1f0",
            )

        assert result["instance_id"] == "i-0abc123def456"
        assert result["state"] == "pending"
        assert result["instance_type"] == "t3.micro"

    @patch("integrations.aws_client._session")
    def test_disallowed_instance_type_raises(self, mock_session):
        from integrations.aws_client import AWSClientError, EC2Client
        from integrations.aws_client import _session
        _session.cache_clear()

        with patch("integrations.aws_client._session") as ms:
            ms.return_value.client.return_value = MagicMock()
            client = EC2Client()
            with pytest.raises(AWSClientError, match="not allowed"):
                client.create_instance(
                    name="hacker",
                    instance_type="p4d.24xlarge",  # not in allowlist
                    ami_id="ami-xxx",
                )

    @patch("integrations.aws_client._session")
    def test_dry_run_success_returns_message(self, mock_session):
        from integrations.aws_client import EC2Client
        from integrations.aws_client import _session
        _session.cache_clear()

        mock_ec2 = MagicMock()
        mock_ec2.run_instances.side_effect = _client_error("DryRunOperation")

        with patch("integrations.aws_client._session") as ms:
            ms.return_value.client.return_value = mock_ec2
            client = EC2Client()
            result = client.create_instance(
                name="dry-test",
                instance_type="t3.micro",
                ami_id="ami-xxx",
                dry_run=True,
            )

        assert result["dry_run"] is True
        assert "permissions OK" in result["message"]

    @patch("integrations.aws_client._session")
    def test_api_error_raises_aws_client_error(self, mock_session):
        from integrations.aws_client import AWSClientError, EC2Client
        from integrations.aws_client import _session
        _session.cache_clear()

        mock_ec2 = MagicMock()
        mock_ec2.run_instances.side_effect = _client_error("InsufficientInstanceCapacity")

        with patch("integrations.aws_client._session") as ms:
            ms.return_value.client.return_value = mock_ec2
            client = EC2Client()
            with pytest.raises(AWSClientError, match="run_instances failed"):
                client.create_instance("x", "t3.micro", "ami-xxx")

    @patch("integrations.aws_client._session")
    def test_optional_params_forwarded(self, mock_session):
        from integrations.aws_client import EC2Client
        from integrations.aws_client import _session
        _session.cache_clear()

        mock_ec2 = MagicMock()
        mock_ec2.run_instances.return_value = {
            "Instances": [{
                "InstanceId": "i-opt123",
                "State": {"Name": "pending"},
                "InstanceType": "t3.small",
                "ImageId": "ami-xxx",
                "Placement": {"AvailabilityZone": "us-east-1b"},
            }]
        }

        with patch("integrations.aws_client._session") as ms:
            ms.return_value.client.return_value = mock_ec2
            client = EC2Client()
            client.create_instance(
                name="with-opts",
                instance_type="t3.small",
                ami_id="ami-xxx",
                key_name="my-key",
                subnet_id="subnet-abc",
                security_group_ids=["sg-1", "sg-2"],
            )

        call_kwargs = mock_ec2.run_instances.call_args[1]
        assert call_kwargs["KeyName"] == "my-key"
        assert call_kwargs["SubnetId"] == "subnet-abc"
        assert call_kwargs["SecurityGroupIds"] == ["sg-1", "sg-2"]


# ── EC2 list_instances ────────────────────────────────────────────────────────

class TestEC2ListInstances:
    @patch("integrations.aws_client._session")
    def test_list_instances_returns_parsed_list(self, mock_session):
        from integrations.aws_client import EC2Client
        from integrations.aws_client import _session
        _session.cache_clear()

        mock_ec2 = MagicMock()
        mock_ec2.describe_instances.return_value = {
            "Reservations": [{
                "Instances": [{
                    "InstanceId": "i-001",
                    "State": {"Name": "running"},
                    "InstanceType": "t3.micro",
                    "Tags": [{"Key": "Name", "Value": "web-server"}],
                    "PublicIpAddress": "1.2.3.4",
                    "PrivateIpAddress": "10.0.0.1",
                }]
            }]
        }

        with patch("integrations.aws_client._session") as ms:
            ms.return_value.client.return_value = mock_ec2
            client = EC2Client()
            result = client.list_instances()

        assert len(result) == 1
        assert result[0]["instance_id"] == "i-001"
        assert result[0]["name"] == "web-server"
        assert result[0]["public_ip"] == "1.2.3.4"

    @patch("integrations.aws_client._session")
    def test_no_instances_returns_empty_list(self, mock_session):
        from integrations.aws_client import EC2Client
        from integrations.aws_client import _session
        _session.cache_clear()

        mock_ec2 = MagicMock()
        mock_ec2.describe_instances.return_value = {"Reservations": []}

        with patch("integrations.aws_client._session") as ms:
            ms.return_value.client.return_value = mock_ec2
            client = EC2Client()
            result = client.list_instances()

        assert result == []

    @patch("integrations.aws_client._session")
    def test_filter_passed_to_boto3(self, mock_session):
        from integrations.aws_client import EC2Client
        from integrations.aws_client import _session
        _session.cache_clear()

        mock_ec2 = MagicMock()
        mock_ec2.describe_instances.return_value = {"Reservations": []}

        filters = [{"Name": "instance-state-name", "Values": ["running"]}]
        with patch("integrations.aws_client._session") as ms:
            ms.return_value.client.return_value = mock_ec2
            client = EC2Client()
            client.list_instances(filters=filters)

        mock_ec2.describe_instances.assert_called_once_with(Filters=filters)


# ── S3 list_buckets ───────────────────────────────────────────────────────────

class TestS3ListBuckets:
    @patch("integrations.aws_client._session")
    def test_list_buckets_returns_parsed_list(self, mock_session):
        from integrations.aws_client import S3Client
        from integrations.aws_client import _session
        _session.cache_clear()

        from datetime import datetime, timezone
        mock_s3 = MagicMock()
        mock_s3.list_buckets.return_value = {
            "Buckets": [
                {"Name": "my-prod-bucket", "CreationDate": datetime(2024, 1, 1, tzinfo=timezone.utc)},
                {"Name": "my-logs-bucket", "CreationDate": datetime(2024, 2, 1, tzinfo=timezone.utc)},
            ]
        }

        with patch("integrations.aws_client._session") as ms:
            ms.return_value.client.return_value = mock_s3
            client = S3Client()
            result = client.list_buckets()

        assert len(result) == 2
        assert result[0]["name"] == "my-prod-bucket"

    @patch("integrations.aws_client._session")
    def test_empty_account_returns_empty_list(self, mock_session):
        from integrations.aws_client import S3Client
        from integrations.aws_client import _session
        _session.cache_clear()

        mock_s3 = MagicMock()
        mock_s3.list_buckets.return_value = {"Buckets": []}

        with patch("integrations.aws_client._session") as ms:
            ms.return_value.client.return_value = mock_s3
            client = S3Client()
            result = client.list_buckets()

        assert result == []


# ── S3 create_bucket ──────────────────────────────────────────────────────────

class TestS3CreateBucket:
    @patch("integrations.aws_client._session")
    def test_create_bucket_success(self, mock_session):
        from integrations.aws_client import S3Client
        from integrations.aws_client import _session
        _session.cache_clear()

        mock_s3 = MagicMock()

        with patch("integrations.aws_client._session") as ms:
            ms.return_value.client.return_value = mock_s3
            ms.return_value.region_name = "us-east-1"
            client = S3Client()
            result = client.create_bucket("my-new-bucket")

        assert result["bucket"] == "my-new-bucket"
        assert result["public_access"] == "blocked"

    @patch("integrations.aws_client._session")
    def test_public_access_block_always_called(self, mock_session):
        from integrations.aws_client import S3Client
        from integrations.aws_client import _session
        _session.cache_clear()

        mock_s3 = MagicMock()

        with patch("integrations.aws_client._session") as ms:
            ms.return_value.client.return_value = mock_s3
            ms.return_value.region_name = "us-east-1"
            client = S3Client()
            client.create_bucket("secure-bucket")

        mock_s3.put_public_access_block.assert_called_once()
        block_cfg = mock_s3.put_public_access_block.call_args[1]["PublicAccessBlockConfiguration"]
        assert block_cfg["BlockPublicAcls"] is True
        assert block_cfg["BlockPublicPolicy"] is True

    @patch("integrations.aws_client._session")
    def test_non_us_east_1_includes_location_constraint(self, mock_session):
        from integrations.aws_client import S3Client
        from integrations.aws_client import _session
        _session.cache_clear()

        mock_s3 = MagicMock()

        with patch("integrations.aws_client._session") as ms:
            ms.return_value.client.return_value = mock_s3
            ms.return_value.region_name = "eu-west-1"
            client = S3Client()
            client.create_bucket("eu-bucket", region="eu-west-1")

        call_kwargs = mock_s3.create_bucket.call_args[1]
        assert "CreateBucketConfiguration" in call_kwargs
        assert call_kwargs["CreateBucketConfiguration"]["LocationConstraint"] == "eu-west-1"

    @patch("integrations.aws_client._session")
    def test_create_bucket_api_error_raises(self, mock_session):
        from integrations.aws_client import AWSClientError, S3Client
        from integrations.aws_client import _session
        _session.cache_clear()

        mock_s3 = MagicMock()
        mock_s3.create_bucket.side_effect = _client_error("BucketAlreadyExists")

        with patch("integrations.aws_client._session") as ms:
            ms.return_value.client.return_value = mock_s3
            ms.return_value.region_name = "us-east-1"
            client = S3Client()
            with pytest.raises(AWSClientError, match="create_bucket failed"):
                client.create_bucket("already-taken")
