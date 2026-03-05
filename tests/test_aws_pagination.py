from types import SimpleNamespace

from app.tools import aws_tools


class _FakeEC2Paginator:
    def paginate(self):
        return [
            {
                "Reservations": [
                    {
                        "Instances": [
                            {
                                "InstanceId": "i-1",
                                "InstanceType": "t3.micro",
                                "State": {"Name": "running"},
                                "Tags": [{"Key": "Name", "Value": "web-1"}],
                            }
                        ]
                    }
                ]
            }
        ]


class _FakeEC2Client:
    def get_paginator(self, name):
        assert name == "describe_instances"
        return _FakeEC2Paginator()


class _FakeECSPaginator:
    def paginate(self):
        return [{"clusterArns": ["arn:1", "arn:2"]}]


class _FakeECSClient:
    def get_paginator(self, name):
        assert name == "list_clusters"
        return _FakeECSPaginator()

    def describe_clusters(self, clusters):
        return {
            "clusters": [
                {
                    "clusterName": "main",
                    "clusterArn": clusters[0],
                    "status": "ACTIVE",
                    "runningTasksCount": 1,
                    "pendingTasksCount": 0,
                    "activeServicesCount": 1,
                }
            ]
        }


def test_ec2_uses_pagination(monkeypatch):
    monkeypatch.setattr(aws_tools, "settings", SimpleNamespace(aws_max_pages=5, aws_default_cost_days=30))
    monkeypatch.setattr(
        aws_tools.boto3,
        "client",
        lambda service, region_name=None: _FakeEC2Client() if service == "ec2" else None,
    )

    result = aws_tools.list_aws_ec2_instances("us-east-1")

    assert result["status"] == "success"
    assert result["instances"][0]["id"] == "i-1"
    assert result["pages_scanned"] == 1


def test_ecs_uses_pagination(monkeypatch):
    monkeypatch.setattr(aws_tools, "settings", SimpleNamespace(aws_max_pages=5, aws_default_cost_days=30))
    monkeypatch.setattr(
        aws_tools.boto3,
        "client",
        lambda service, region_name=None: _FakeECSClient() if service == "ecs" else None,
    )

    result = aws_tools.list_aws_ecs_clusters("us-east-1")

    assert result["status"] == "success"
    assert result["clusters"][0]["name"] == "main"
    assert result["pages_scanned"] == 1
