# DevOps MCP Server

> **MCP name: io.github.maripeddisupraj/devops-mcp-server**
>
> A **production-grade Model Context Protocol (MCP) server** that exposes 103 tools across Terraform, GitHub, AWS, Kubernetes, Helm, Azure, GCP, ArgoCD, HashiCorp Vault, and PagerDuty as structured JSON tool APIs — designed for AI agents (LangGraph, AutoGen, Claude) to automate DevOps workflows end-to-end.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.0-green)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Table of Contents

- [What is This?](#what-is-this)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [Claude Desktop Integration](#claude-desktop-integration)
- [Docker](#docker)
- [Tool Reference](#tool-reference)
  - [Terraform Tools](#terraform-tools)
  - [GitHub Tools](#github-tools)
  - [AWS Tools](#aws-tools)
  - [Kubernetes Tools](#kubernetes-tools)
  - [Helm Tools](#helm-tools)
  - [Azure Tools](#azure-tools)
  - [GCP Tools](#gcp-tools)
  - [ArgoCD Tools](#argocd-tools)
  - [HashiCorp Vault Tools](#hashicorp-vault-tools)
  - [PagerDuty Tools](#pagerduty-tools)
- [Example Workflows](#example-workflows)
- [Adding a New Tool](#adding-a-new-tool)
- [Running Tests](#running-tests)
- [Security Model](#security-model)
- [Troubleshooting](#troubleshooting)

---

## What is This?

This server implements the [Model Context Protocol](https://modelcontextprotocol.io) — a standard that lets AI agents discover and invoke tools over HTTP or stdio. Instead of hard-coding SDK calls into your AI agent, you point it at this server and it dynamically discovers what DevOps operations are available.

**Without MCP:**

```text
Agent → custom boto3 code → AWS
Agent → custom subprocess → Terraform
Agent → custom SDK calls → Azure / GCP / K8s / ...
```

**With MCP:**

```text
Agent → POST /tools/execute → MCP Server → AWS / Terraform / GitHub / K8s / Azure / GCP / ...
```

The agent calls one endpoint with a tool name and JSON inputs. The server handles all SDK complexity, authentication, validation, and error formatting across **10 platforms with 103 tools**.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                          AI Agent                               │
│          (Claude / LangGraph / AutoGen / custom)                │
└───────────────────────────┬─────────────────────────────────────┘
                            │ POST /tools/execute  OR  stdio (MCP)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI MCP Server                          │
│                                                                 │
│   GET /tools          →  ToolRegistry (list all 103 tools)      │
│   POST /tools/execute →  ToolExecutor (validate + run)          │
│   GET /tools/{name}   →  ToolRegistry (describe one tool)       │
│   GET /metrics        →  Prometheus metrics                     │
└──────────┬──────────────────────────────────────────────────────┘
           │
    ┌──────┴──────────────────────────────────────────────────┐
    │                    Tool Handlers (10 services)           │
    │  terraform/  github/  aws/  kubernetes/  helm/           │
    │  azure/      gcp/     argocd/  vault/    pagerduty/      │
    └──────┬──────────────────────────────────────────────────┘
           │
    ┌──────┴──────────────────────────────────────────────────┐
    │                      Integrations                        │
    │  subprocess(tf/helm)  PyGithub   boto3   k8s-client     │
    │  azure-sdk            google-cloud-sdk   httpx(rest)    │
    └─────────────────────────────────────────────────────────┘
```

**Request lifecycle:**

1. Agent sends `POST /tools/execute` with `tool_name` and `inputs`
2. `ToolExecutor` validates inputs against the tool's JSON Schema
3. Handler is resolved from `ToolRegistry`
4. Handler calls the integration (boto3, PyGithub, subprocess, httpx, etc.)
5. Result wrapped in `{"status": "success"|"error", "data": ..., "error": ...}`
6. Execution logged to SQLite audit DB + optional Slack notification

---

## Project Structure

```text
devops-mcp-server/
│
├── server/
│   ├── main.py              # FastAPI app — all HTTP routes
│   ├── mcp_stdio.py         # MCP stdio transport for Claude Desktop
│   ├── registry.py          # Tool registration — build_registry()
│   ├── executor.py          # ToolExecutor — validate + dispatch
│   └── schemas.py           # Pydantic request/response models
│
├── core/
│   ├── config.py            # pydantic-settings — all env vars
│   ├── auth.py              # API key middleware + cloud credential helpers
│   ├── logger.py            # structlog structured logging
│   └── audit.py             # SQLite audit trail (WAL mode)
│
├── tools/
│   ├── terraform/           # plan, apply, destroy, init, validate, output, state_list
│   ├── github/              # create_pr, get_repo, list_issues, trigger_workflow,
│   │                        #   create_release, create_issue, merge_pr, get_workflow_run
│   ├── aws/                 # ec2, s3, lambda, rds, ec2_lifecycle, s3_objects,
│   │                        #   cloudwatch, secrets, networking, iam, rds_crud,
│   │                        #   ecs, cost, ecr, alb
│   ├── kubernetes/          # deploy, get_pods, get_logs, get_events, scale,
│   │                        #   rollout_restart, rollout_status, get_deployments,
│   │                        #   get_services, get_nodes, delete_pod,
│   │                        #   namespace, configmap, secret, jobs, ingress
│   ├── helm/                # list, install, upgrade, rollback, status
│   ├── azure/               # rg_list, vm_list, vm_start, vm_stop,
│   │                        #   aks_list, acr_list, kv_get, kv_set
│   ├── gcp/                 # instances, buckets, gke, cloudrun,
│   │                        #   cloudsql, cloudbuild_list, cloudbuild_trigger
│   ├── argocd/              # list, status, sync, rollback
│   ├── vault/               # read, write, list
│   └── pagerduty/           # list_incidents, acknowledge, resolve, create
│
├── integrations/
│   ├── terraform_runner.py  # Terraform subprocess wrapper
│   ├── helm_runner.py       # Helm subprocess wrapper
│   ├── aws_client.py        # boto3 client classes (13 services)
│   ├── github_client.py     # PyGithub wrapper
│   ├── k8s_client.py        # kubernetes-client/python wrapper
│   ├── azure_client.py      # Azure SDK client classes
│   ├── gcp_client.py        # GCP SDK client classes
│   ├── argocd_client.py     # ArgoCD REST API (httpx)
│   ├── vault_client.py      # Vault KV v2 REST API (httpx)
│   └── pagerduty_client.py  # PagerDuty REST API v2 (httpx)
│
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml           # PyPI packaging
├── requirements.txt
└── .env.example
```

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/MaripeddiSupraj/devops-mcp-server.git
cd devops-mcp-server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials (see Configuration section)
```

### 3. Start the server

```bash
uvicorn server.main:app --reload
# Server runs on http://localhost:8000
```

### 4. Discover tools

```bash
curl http://localhost:8000/tools | python -m json.tool | head -60
```

### 5. Execute a tool

```bash
curl -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "aws_list_ec2_instances", "inputs": {"region": "us-east-1"}}'
```

---

## Configuration

All settings are read from environment variables (or `.env` file). Only configure the services you actually use.

### Core Server

| Variable | Default | Description |
|---|---|---|
| `SERVER_HOST` | `0.0.0.0` | Bind host |
| `SERVER_PORT` | `8000` | Bind port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DRY_RUN` | `false` | Skip mutating operations |
| `MCP_API_KEY` | *(none)* | API key for request auth (leave unset for dev) |
| `ENVIRONMENT` | `development` | Runtime label |
| `CORS_ORIGINS` | `*` | Comma-separated CORS origins |
| `AUDIT_DB_PATH` | `audit.db` | SQLite audit log path |
| `TOOL_TIMEOUT_SECONDS` | `120` | Default per-tool timeout |

### GitHub

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | Personal access token with repo scope |

### AWS

| Variable | Default | Description |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | *(none)* | AWS access key (or use instance profile) |
| `AWS_SECRET_ACCESS_KEY` | *(none)* | AWS secret key |
| `AWS_REGION` | `us-east-1` | Default region |

### Kubernetes

| Variable | Description |
|---|---|
| `KUBECONFIG` | Path to kubeconfig file (defaults to `~/.kube/config`) |

### Terraform

| Variable | Default | Description |
|---|---|---|
| `TERRAFORM_BINARY` | `terraform` | Path to terraform binary |
| `TERRAFORM_ALLOWED_BASE_DIR` | `/tmp/terraform` | Root directory for allowed Terraform paths |
| `TERRAFORM_TIMEOUT_SECONDS` | `600` | Max seconds per Terraform command |

### Helm

| Variable | Default | Description |
|---|---|---|
| `HELM_BINARY` | `helm` | Path to helm binary |
| `HELM_TIMEOUT_SECONDS` | `300` | Max seconds per Helm command |

### Azure

| Variable | Description |
|---|---|
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `AZURE_TENANT_ID` | Azure tenant ID |
| `AZURE_CLIENT_ID` | Service principal client ID |
| `AZURE_CLIENT_SECRET` | Service principal client secret |

### GCP

| Variable | Description |
|---|---|
| `GCP_PROJECT_ID` | GCP project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON key file |

### ArgoCD

| Variable | Default | Description |
|---|---|---|
| `ARGOCD_SERVER_URL` | *(none)* | ArgoCD server URL (e.g. `https://argocd.example.com`) |
| `ARGOCD_AUTH_TOKEN` | *(none)* | ArgoCD API token |
| `ARGOCD_INSECURE` | `false` | Skip TLS verification |

### HashiCorp Vault

| Variable | Default | Description |
|---|---|---|
| `VAULT_ADDR` | *(none)* | Vault server address (e.g. `https://vault.example.com`) |
| `VAULT_TOKEN` | *(none)* | Vault token |
| `VAULT_NAMESPACE` | *(none)* | Vault namespace (Enterprise only) |
| `VAULT_MOUNT` | `secret` | KV v2 mount path |

### PagerDuty

| Variable | Description |
|---|---|
| `PAGERDUTY_API_KEY` | PagerDuty REST API v2 key |
| `PAGERDUTY_EMAIL` | Email address for incident creation (From header) |
| `PAGERDUTY_SERVICE_ID` | Default service ID for new incidents |

### Slack (optional)

| Variable | Description |
|---|---|
| `SLACK_WEBHOOK_URL` | Incoming webhook URL for tool notifications |

---

## Running the Server

### HTTP mode (API / agent usage)

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

### stdio mode (Claude Desktop)

```bash
python -m server.mcp_stdio
# or after pip install:
devops-mcp-server
```

### Available endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/tools` | List all registered tools |
| `GET` | `/tools?tag=aws` | Filter tools by tag |
| `GET` | `/tools/{name}` | Describe a single tool |
| `POST` | `/tools/execute` | Execute a tool |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Prometheus metrics |

---

## Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "devops": {
      "command": "devops-mcp-server",
      "env": {
        "GITHUB_TOKEN": "ghp_...",
        "AWS_ACCESS_KEY_ID": "AKIA...",
        "AWS_SECRET_ACCESS_KEY": "...",
        "AWS_REGION": "us-east-1",
        "KUBECONFIG": "/home/user/.kube/config",
        "AZURE_SUBSCRIPTION_ID": "...",
        "AZURE_TENANT_ID": "...",
        "AZURE_CLIENT_ID": "...",
        "AZURE_CLIENT_SECRET": "...",
        "GCP_PROJECT_ID": "my-project",
        "GOOGLE_APPLICATION_CREDENTIALS": "/home/user/gcp-key.json",
        "ARGOCD_SERVER_URL": "https://argocd.example.com",
        "ARGOCD_AUTH_TOKEN": "...",
        "VAULT_ADDR": "https://vault.example.com",
        "VAULT_TOKEN": "...",
        "PAGERDUTY_API_KEY": "..."
      }
    }
  }
}
```

---

## Docker

```bash
# Build
docker build -t devops-mcp-server .

# Run with env file
docker run --env-file .env -p 8000:8000 devops-mcp-server

# Or with docker-compose
docker-compose up
```

---

## Tool Reference

### Terraform Tools

| Tool | Description |
|---|---|
| `terraform_plan` | Run `terraform plan` in a directory; returns the plan output |
| `terraform_apply` | Run `terraform apply -auto-approve`; returns apply output |
| `terraform_destroy` | Run `terraform destroy -auto-approve`; destructive |
| `terraform_init` | Run `terraform init` to initialize providers and modules |
| `terraform_validate` | Run `terraform validate` to check configuration syntax |
| `terraform_output` | Run `terraform output -json` to retrieve output values |
| `terraform_state_list` | Run `terraform state list` to enumerate managed resources |

**Required env:** `TERRAFORM_BINARY` (defaults to `terraform` on PATH)

---

### GitHub Tools

| Tool | Description |
|---|---|
| `github_create_pr` | Create a pull request in a repository |
| `github_get_repo` | Get metadata for a repository |
| `github_list_issues` | List open issues, optionally filtered by label |
| `github_trigger_workflow` | Trigger a workflow dispatch event |
| `github_create_release` | Create a tagged release with release notes |
| `github_create_issue` | Create a new issue with title, body, and labels |
| `github_merge_pr` | Merge an open pull request by number |
| `github_get_workflow_run` | Get the status and conclusion of a workflow run |

**Required env:** `GITHUB_TOKEN`

---

### AWS Tools

#### EC2

| Tool | Description |
|---|---|
| `aws_describe_ec2_instance` | Describe a specific EC2 instance by ID |
| `aws_list_ec2_instances` | List EC2 instances, optionally filtered by state |
| `aws_stop_ec2_instance` | Stop a running EC2 instance |
| `aws_start_ec2_instance` | Start a stopped EC2 instance |
| `aws_terminate_ec2_instance` | Terminate an EC2 instance (destructive) |

#### S3

| Tool | Description |
|---|---|
| `aws_list_s3_buckets` | List all S3 buckets in the account |
| `aws_create_s3_bucket` | Create a new S3 bucket |
| `aws_list_s3_objects` | List objects in a bucket with optional prefix filter |
| `aws_upload_s3_object` | Upload text content to an S3 object |

#### Lambda

| Tool | Description |
|---|---|
| `aws_list_lambda_functions` | List Lambda functions, optionally filtered by runtime |
| `aws_invoke_lambda` | Invoke a Lambda function synchronously |

#### RDS

| Tool | Description |
|---|---|
| `aws_list_rds_instances` | List RDS DB instances |
| `aws_rds_create_instance` | Create a new RDS DB instance |
| `aws_rds_create_snapshot` | Create a snapshot of an RDS instance |
| `aws_rds_restore_from_snapshot` | Restore an RDS instance from a snapshot |

#### CloudWatch

| Tool | Description |
|---|---|
| `aws_cloudwatch_get_metrics` | Retrieve CloudWatch metric statistics |
| `aws_cloudwatch_list_alarms` | List CloudWatch alarms with optional state filter |
| `aws_cloudwatch_list_log_groups` | List CloudWatch Log Groups |
| `aws_cloudwatch_query_logs` | Run a CloudWatch Logs Insights query |

#### Secrets Manager & SSM

| Tool | Description |
|---|---|
| `aws_secrets_get` | Retrieve a secret value from Secrets Manager |
| `aws_secrets_create` | Create a new secret in Secrets Manager |
| `aws_ssm_get_parameter` | Get a parameter from SSM Parameter Store |
| `aws_ssm_put_parameter` | Put/update a parameter in SSM Parameter Store |

#### Networking

| Tool | Description |
|---|---|
| `aws_list_vpcs` | List VPCs in the region |
| `aws_list_security_groups` | List EC2 security groups |
| `aws_list_route53_zones` | List Route 53 hosted zones |

#### IAM

| Tool | Description |
|---|---|
| `aws_iam_list_roles` | List IAM roles with optional path prefix filter |
| `aws_iam_list_policies` | List IAM customer-managed policies |
| `aws_iam_simulate_policy` | Simulate IAM policy evaluation for an action/resource |

#### ECS

| Tool | Description |
|---|---|
| `aws_ecs_list_clusters` | List ECS clusters |
| `aws_ecs_list_services` | List services in an ECS cluster |
| `aws_ecs_list_tasks` | List running tasks in an ECS cluster |
| `aws_ecs_deploy_service` | Force a new deployment of an ECS service |

#### ECR

| Tool | Description |
|---|---|
| `aws_ecr_list_repositories` | List ECR repositories |
| `aws_ecr_list_images` | List images in an ECR repository |

#### ALB / Load Balancing

| Tool | Description |
|---|---|
| `aws_alb_list` | List Application/Network Load Balancers |
| `aws_alb_list_target_groups` | List ALB target groups |

#### Cost Explorer

| Tool | Description |
|---|---|
| `aws_cost_by_service` | Get AWS cost breakdown by service for a date range |
| `aws_cost_monthly_total` | Get total monthly AWS spend |

**Required env:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`

---

### Kubernetes Tools

#### Workloads

| Tool | Description |
|---|---|
| `kubernetes_deploy` | Deploy or update a deployment with a new image |
| `kubernetes_get_pods` | List pods in a namespace |
| `kubernetes_get_logs` | Get logs from a pod container |
| `kubernetes_get_events` | Get events for a namespace |
| `kubernetes_scale` | Scale a deployment to N replicas |
| `kubernetes_rollout_restart` | Trigger a rolling restart of a deployment |
| `kubernetes_rollout_status` | Check the rollout status of a deployment |
| `kubernetes_get_deployments` | List deployments in a namespace |
| `kubernetes_delete_pod` | Delete a pod (triggers restart) |

#### Services & Networking

| Tool | Description |
|---|---|
| `kubernetes_get_services` | List services in a namespace |
| `kubernetes_list_ingresses` | List Ingress resources in a namespace |

#### Cluster

| Tool | Description |
|---|---|
| `kubernetes_get_nodes` | List cluster nodes with status and capacity |
| `kubernetes_list_namespaces` | List all namespaces |
| `kubernetes_create_namespace` | Create a new namespace |

#### Config & Secrets

| Tool | Description |
|---|---|
| `kubernetes_get_configmap` | Get a ConfigMap and its data |
| `kubernetes_apply_configmap` | Create or update a ConfigMap |
| `kubernetes_list_secrets` | List secret names in a namespace (keys only, not values) |

#### Batch

| Tool | Description |
|---|---|
| `kubernetes_list_jobs` | List Jobs in a namespace |
| `kubernetes_list_cronjobs` | List CronJobs in a namespace |

**Required env:** `KUBECONFIG`

---

### Helm Tools

| Tool | Description |
|---|---|
| `helm_list` | List Helm releases in a namespace |
| `helm_install` | Install a Helm chart as a named release |
| `helm_upgrade` | Upgrade an existing Helm release |
| `helm_rollback` | Roll back a release to a previous revision |
| `helm_status` | Get the status of a Helm release |

**Required env:** `HELM_BINARY` (defaults to `helm` on PATH), `KUBECONFIG`

---

### Azure Tools

| Tool | Description |
|---|---|
| `azure_list_resource_groups` | List all resource groups in the subscription |
| `azure_list_vms` | List VMs in a resource group |
| `azure_start_vm` | Start an Azure virtual machine |
| `azure_stop_vm` | Deallocate (stop) an Azure virtual machine |
| `azure_list_aks_clusters` | List AKS clusters in a resource group |
| `azure_list_acr_registries` | List Azure Container Registries in a resource group |
| `azure_keyvault_get_secret` | Get a secret from Azure Key Vault |
| `azure_keyvault_set_secret` | Set a secret in Azure Key Vault |

**Required env:** `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`

---

### GCP Tools

| Tool | Description |
|---|---|
| `gcp_list_compute_instances` | List Compute Engine instances in a zone |
| `gcp_list_storage_buckets` | List Cloud Storage buckets in the project |
| `gcp_list_gke_clusters` | List GKE clusters in a region |
| `gcp_list_cloud_run_services` | List Cloud Run services in a region |
| `gcp_list_cloud_sql_instances` | List Cloud SQL instances in the project |
| `gcp_list_cloud_builds` | List recent Cloud Build builds |
| `gcp_trigger_cloud_build` | Trigger a Cloud Build via a trigger ID |

**Required env:** `GCP_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`

---

### ArgoCD Tools

| Tool | Description |
|---|---|
| `argocd_list_apps` | List all ArgoCD applications with sync status |
| `argocd_get_app` | Get detailed status for a single application |
| `argocd_sync_app` | Trigger a sync for an ArgoCD application |
| `argocd_rollback_app` | Roll back an application to a previous revision |

**Required env:** `ARGOCD_SERVER_URL`, `ARGOCD_AUTH_TOKEN`

---

### HashiCorp Vault Tools

| Tool | Description |
|---|---|
| `vault_read_secret` | Read a secret from the KV v2 store |
| `vault_write_secret` | Write key-value data to the KV v2 store |
| `vault_list_secrets` | List secret keys at a path in the KV v2 store |

**Required env:** `VAULT_ADDR`, `VAULT_TOKEN`

---

### PagerDuty Tools

| Tool | Description |
|---|---|
| `pagerduty_list_incidents` | List incidents, optionally filtered by status |
| `pagerduty_acknowledge_incident` | Acknowledge an incident by ID |
| `pagerduty_resolve_incident` | Resolve an incident by ID |
| `pagerduty_create_incident` | Create a new incident for a service |

**Required env:** `PAGERDUTY_API_KEY`, `PAGERDUTY_EMAIL` (for create)

---

## Tool Summary

| Service | Tools | Tags |
|---|---|---|
| Terraform | 7 | `terraform`, `iac` |
| GitHub | 8 | `github`, `scm`, `ci` |
| AWS EC2 | 5 | `aws`, `ec2`, `compute` |
| AWS S3 | 4 | `aws`, `s3`, `storage` |
| AWS Lambda | 2 | `aws`, `lambda`, `serverless` |
| AWS RDS | 4 | `aws`, `rds`, `database` |
| AWS CloudWatch | 4 | `aws`, `cloudwatch`, `observability` |
| AWS Secrets/SSM | 4 | `aws`, `secrets`, `ssm` |
| AWS Networking | 3 | `aws`, `networking`, `vpc` |
| AWS IAM | 3 | `aws`, `iam`, `security` |
| AWS ECS | 4 | `aws`, `ecs`, `compute` |
| AWS ECR | 2 | `aws`, `ecr`, `containers` |
| AWS ALB | 2 | `aws`, `networking`, `alb` |
| AWS Cost Explorer | 2 | `aws`, `cost`, `finops` |
| Kubernetes | 19 | `kubernetes`, `k8s` |
| Helm | 5 | `helm`, `kubernetes` |
| Azure | 8 | `azure`, `multicloud` |
| GCP | 7 | `gcp`, `multicloud` |
| ArgoCD | 4 | `argocd`, `gitops` |
| HashiCorp Vault | 3 | `vault`, `secrets` |
| PagerDuty | 4 | `pagerduty`, `incident` |
| **Total** | **103** | |

---

## Example Workflows

### Incident response workflow

```python
# 1. Detect incident
incidents = execute_tool("pagerduty_list_incidents", {"status": "triggered"})

# 2. Acknowledge it
execute_tool("pagerduty_acknowledge_incident", {"incident_id": "P1234AB"})

# 3. Check CloudWatch alarms
execute_tool("aws_cloudwatch_list_alarms", {"state_value": "ALARM"})

# 4. Pull recent logs
execute_tool("aws_cloudwatch_query_logs", {
    "log_group": "/aws/lambda/api",
    "query": "fields @timestamp, @message | filter @message like /ERROR/ | limit 20",
    "minutes": 30
})

# 5. Restart the affected pod
execute_tool("kubernetes_rollout_restart", {"deployment": "api", "namespace": "production"})

# 6. Resolve after fix
execute_tool("pagerduty_resolve_incident", {"incident_id": "P1234AB"})
```

### Multi-cloud deployment workflow

```python
# Deploy to AWS ECS
execute_tool("aws_ecs_deploy_service", {
    "cluster": "production",
    "service": "api",
    "force_new_deployment": True
})

# Upgrade Azure AKS workload via Helm
execute_tool("helm_upgrade", {
    "release": "api",
    "chart": "myrepo/api",
    "namespace": "production",
    "values": {"image.tag": "v2.1.0"}
})

# Sync GCP Cloud Run via ArgoCD
execute_tool("argocd_sync_app", {"app_name": "cloud-run-api"})
```

### GitOps release workflow

```python
# 1. Create a GitHub release
execute_tool("github_create_release", {
    "owner": "my-org", "repo": "api",
    "tag": "v2.1.0", "name": "v2.1.0",
    "body": "Release notes..."
})

# 2. Trigger CI workflow
execute_tool("github_trigger_workflow", {
    "owner": "my-org", "repo": "api",
    "workflow_id": "deploy.yml", "ref": "main"
})

# 3. Apply Terraform for infra changes
execute_tool("terraform_apply", {"working_dir": "/infra/prod"})

# 4. Sync ArgoCD
execute_tool("argocd_sync_app", {"app_name": "api-production"})
```

---

## Adding a New Tool

1. **Create the tool file** in `tools/<service>/my_tool.py`:

```python
TOOL_NAME = "my_service_my_action"
TOOL_DESCRIPTION = "One-line description for AI agents."
TOOL_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "param": {"type": "string", "description": "..."},
    },
    "required": ["param"],
    "additionalProperties": False,
}

def handler(param: str):
    # call your integration
    return {"result": param}
```

2. **Register it** in `server/registry.py`:

```python
from tools.my_service import my_tool

registry.register(ToolEntry(
    name=my_tool.TOOL_NAME,
    description=my_tool.TOOL_DESCRIPTION,
    input_schema=my_tool.TOOL_INPUT_SCHEMA,
    handler=my_tool.handler,
    tags=["my_service"],
))
```

That's it. No other files need to change.

---

## Running Tests

```bash
pip install pytest pytest-asyncio pytest-mock
pytest tests/ -v
```

---

## Security Model

- **API key auth**: Set `MCP_API_KEY` to require `Authorization: Bearer <key>` or `X-API-Key: <key>` on all requests. Leave unset for dev/local.
- **Terraform sandboxing**: All Terraform working directories are validated to reside under `TERRAFORM_ALLOWED_BASE_DIR`. Path traversal is blocked.
- **Helm sandboxing**: Helm binary path is configurable; no shell=True is used.
- **K8s secrets**: `kubernetes_list_secrets` returns key names only — secret values are never returned.
- **Vault**: Read and write operations use token-based auth. Namespace and mount are configurable.
- **Audit log**: Every tool execution (name, inputs hash, status, duration) is logged to SQLite.
- **DRY_RUN mode**: Set `DRY_RUN=true` to block all mutating operations without changing application code.
- **CORS**: Set `CORS_ORIGINS` to explicit origins in production. Avoid `*` outside local dev.
- **Destructive tag**: Tools tagged `destructive` (terminate EC2, Terraform destroy) are clearly labelled. Wire additional confirmation logic in your agent if needed.

---

## Troubleshooting

### "Tool not found"

```bash
curl http://localhost:8000/tools | python -m json.tool | grep '"name"'
```

Verify the tool name matches exactly (case-sensitive).

### AWS authentication errors

```bash
aws sts get-caller-identity
```

Confirm your credentials are valid. The server uses the same credential chain as the AWS CLI (env vars → instance profile → ~/.aws/credentials).

### Kubernetes connection refused

```bash
kubectl cluster-info
```

Confirm `KUBECONFIG` is set and the cluster is reachable.

### Azure authentication errors

Verify all four Azure env vars are set: `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`. The server uses `DefaultAzureCredential`.

### GCP authentication errors

```bash
gcloud auth application-default print-access-token
```

Or set `GOOGLE_APPLICATION_CREDENTIALS` to the path of a service account JSON key.

### ArgoCD / Vault / PagerDuty connection errors

These use plain HTTP (httpx). Confirm the server URL is reachable and the auth token is valid:

```bash
curl -H "Authorization: Bearer $ARGOCD_AUTH_TOKEN" $ARGOCD_SERVER_URL/api/v1/applications
curl -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/health
curl -H "Authorization: Token token=$PAGERDUTY_API_KEY" https://api.pagerduty.com/incidents
```

### Terraform timeout

Increase `TERRAFORM_TIMEOUT_SECONDS` (default 600). Long `apply` runs against large state files may need 900–1800s.

### Helm timeout

Increase `HELM_TIMEOUT_SECONDS` (default 300). Complex chart installs with many resources may take longer.

---

## License

MIT — see [LICENSE](LICENSE).
