# DevOps MCP Server

> **MCP name: io.github.maripeddisupraj/devops-mcp-server**
>
> A **production-grade Model Context Protocol (MCP) server** that exposes **160 tools across 20 services** — Terraform, GitHub, GitLab, AWS, Kubernetes, Helm, Azure, GCP, ArgoCD, HashiCorp Vault, PagerDuty, Datadog, Docker, Jenkins, Cloudflare, Ansible, and more — as structured JSON tool APIs designed for AI agents to automate DevOps workflows end-to-end.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.0-green)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tools](https://img.shields.io/badge/tools-160-orange)](https://github.com/MaripeddiSupraj/devops-mcp-server)

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
  - [GitLab Tools](#gitlab-tools)
  - [AWS Tools](#aws-tools)
  - [Kubernetes Tools](#kubernetes-tools)
  - [Helm Tools](#helm-tools)
  - [Azure Tools](#azure-tools)
  - [GCP Tools](#gcp-tools)
  - [ArgoCD Tools](#argocd-tools)
  - [HashiCorp Vault Tools](#hashicorp-vault-tools)
  - [PagerDuty Tools](#pagerduty-tools)
  - [Datadog Tools](#datadog-tools)
  - [Docker Tools](#docker-tools)
  - [Jenkins Tools](#jenkins-tools)
  - [Cloudflare Tools](#cloudflare-tools)
  - [Ansible Tools](#ansible-tools)
  - [Security Scanning Tools](#security-scanning-tools)
  - [GCP Secret Manager Tools](#gcp-secret-manager-tools)
  - [Multi-cloud FinOps Tools](#multi-cloud-finops-tools)
- [Tool Summary](#tool-summary)
- [Example Workflows](#example-workflows)
- [Adding a New Tool](#adding-a-new-tool)
- [Running Tests](#running-tests)
- [Security Model](#security-model)
- [Troubleshooting](#troubleshooting)

---

## What is This?

This server implements the [Model Context Protocol](https://modelcontextprotocol.io) — a standard that lets AI agents discover and invoke tools over HTTP or stdio. Instead of hard-coding SDK calls into your agent, you point it at this server and it dynamically discovers 160 DevOps operations across 20 platforms.

**Without MCP:**

```text
Agent → custom boto3 code → AWS
Agent → custom subprocess → Terraform
Agent → custom SDK → Azure / GCP / K8s / Datadog / ...
```

**With MCP:**

```text
Agent → POST /tools/execute → MCP Server → any of 20 platforms
```

The agent calls one endpoint with a tool name and JSON inputs. The server handles all SDK complexity, authentication, validation, timeout, audit logging, and error formatting.

---

## Architecture

```text
┌────────────────────────────────────────────────────────────────────┐
│                           AI Agent                                 │
│           (Claude / LangGraph / AutoGen / custom)                  │
└────────────────────────┬───────────────────────────────────────────┘
                         │  POST /tools/execute  OR  stdio (MCP)
                         ▼
┌────────────────────────────────────────────────────────────────────┐
│                      FastAPI MCP Server                            │
│                                                                    │
│   GET /tools           →  ToolRegistry (list all 160 tools)        │
│   POST /tools/execute  →  ToolExecutor (validate + run)            │
│   GET /tools/{name}    →  ToolRegistry (describe one tool)         │
│   GET /metrics         →  Prometheus metrics                       │
└──────────┬─────────────────────────────────────────────────────────┘
           │
    ┌──────┴──────────────────────────────────────────────────────┐
    │               Tool Handlers (20 services)                    │
    │  terraform  github   gitlab   aws   kubernetes  helm         │
    │  azure      gcp      argocd   vault  pagerduty  datadog      │
    │  docker     jenkins  cloudflare  ansible  security  finops   │
    └──────┬──────────────────────────────────────────────────────┘
           │
    ┌──────┴──────────────────────────────────────────────────────┐
    │                     Integrations                             │
    │  subprocess(tf/helm/docker/ansible/trivy/tfsec/infracost)   │
    │  boto3  PyGithub  k8s-client  azure-sdk  google-cloud-sdk   │
    │  httpx(argocd/vault/pagerduty/datadog/gitlab/jenkins/cf)    │
    └─────────────────────────────────────────────────────────────┘
```

**Request lifecycle:**

1. Agent sends `POST /tools/execute` with `tool_name` and `inputs`
2. `ToolExecutor` validates inputs against the tool's JSON Schema
3. Handler is resolved from `ToolRegistry` and dispatched
4. Handler calls the integration (boto3, subprocess, httpx, etc.)
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
│   ├── auth.py              # API key middleware + credential helpers
│   ├── logger.py            # structlog structured logging
│   └── audit.py             # SQLite audit trail (WAL mode)
│
├── tools/
│   ├── terraform/           # plan, apply, destroy, init, validate, output, state_list
│   ├── github/              # create_pr, get_repo, list_issues, trigger_workflow,
│   │                        #   create_release, create_issue, merge_pr, get_workflow_run
│   ├── gitlab/              # list_projects, list_mrs, create_mr, merge_mr,
│   │                        #   list_pipelines, trigger_pipeline, list_issues
│   ├── aws/                 # ec2, s3, lambda, rds, ec2_lifecycle, s3_objects,
│   │                        #   cloudwatch, secrets, networking, iam, rds_crud,
│   │                        #   ecs, cost, ecr, alb, sqs, sns, dynamodb
│   ├── kubernetes/          # deploy, get_pods, get_logs, get_events, scale,
│   │                        #   rollout_restart, rollout_status, get_deployments,
│   │                        #   get_services, get_nodes, delete_pod,
│   │                        #   namespace, configmap, secret, jobs, ingress
│   ├── helm/                # list, install, upgrade, rollback, status
│   ├── azure/               # rg_list, vm_list, vm_start, vm_stop,
│   │                        #   aks_list, acr_list, kv_get, kv_set
│   ├── gcp/                 # instances, buckets, gke, cloudrun, cloudsql,
│   │                        #   cloudbuild, secret_manager
│   ├── argocd/              # list, status, sync, rollback
│   ├── vault/               # read, write, list
│   ├── pagerduty/           # list_incidents, acknowledge, resolve, create
│   ├── datadog/             # monitors, metrics, events, dashboards, incidents, hosts
│   ├── docker/              # list_images, pull, build, push, inspect,
│   │                        #   list_containers, logs, tag
│   ├── jenkins/             # list_jobs, get_job, trigger_build, get_build,
│   │                        #   get_build_log, list_builds
│   ├── cloudflare/          # list_zones, dns_records, purge_cache, waf_rules
│   ├── ansible/             # run_playbook, list_hosts, ping, run_module
│   ├── security/            # trivy_scan_image, trivy_scan_filesystem, tfsec_scan
│   └── finops/              # azure_cost, gcp_billing, infracost_estimate
│
├── integrations/
│   ├── terraform_runner.py  # Terraform subprocess wrapper
│   ├── helm_runner.py       # Helm subprocess wrapper
│   ├── docker_runner.py     # Docker CLI subprocess wrapper
│   ├── ansible_runner.py    # Ansible CLI subprocess wrapper
│   ├── scanner_runner.py    # Trivy + tfsec subprocess wrappers
│   ├── aws_client.py        # boto3 client classes (15 services)
│   ├── github_client.py     # PyGithub wrapper
│   ├── gitlab_client.py     # GitLab REST API v4 (httpx)
│   ├── k8s_client.py        # kubernetes-client/python wrapper
│   ├── azure_client.py      # Azure SDK client classes + Cost Management
│   ├── gcp_client.py        # GCP SDK client classes + Secret Manager + Billing
│   ├── argocd_client.py     # ArgoCD REST API (httpx)
│   ├── vault_client.py      # Vault KV v2 REST API (httpx)
│   ├── pagerduty_client.py  # PagerDuty REST API v2 (httpx)
│   ├── datadog_client.py    # Datadog REST API v1/v2 (httpx)
│   ├── jenkins_client.py    # Jenkins REST API (httpx)
│   └── cloudflare_client.py # Cloudflare REST API v4 (httpx)
│
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml           # PyPI packaging (v4.0.0)
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
# Fill in credentials for the services you want to use
```

### 3. Start the server

```bash
uvicorn server.main:app --reload
```

### 4. Verify 160 tools are registered

```bash
curl http://localhost:8000/tools | python -m json.tool | grep '"count"'
```

### 5. Execute a tool

```bash
curl -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "aws_list_ec2_instances", "inputs": {}}'
```

---

## Configuration

All settings are read from environment variables (or `.env` file). Only configure the services you use — unconfigured services will return a clear error when called.

### Core Server

| Variable | Default | Description |
|---|---|---|
| `SERVER_HOST` | `0.0.0.0` | Bind host |
| `SERVER_PORT` | `8000` | Bind port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DRY_RUN` | `false` | Block all mutating operations |
| `MCP_API_KEY` | *(none)* | API key for request auth |
| `ENVIRONMENT` | `development` | Runtime label |
| `CORS_ORIGINS` | `*` | Comma-separated allowed CORS origins |
| `AUDIT_DB_PATH` | `audit.db` | SQLite audit log path |
| `TOOL_TIMEOUT_SECONDS` | `120` | Default per-tool timeout |

### GitHub

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | Personal access token with repo scope |

### GitLab

| Variable | Default | Description |
|---|---|---|
| `GITLAB_TOKEN` | *(none)* | GitLab personal access token |
| `GITLAB_URL` | `https://gitlab.com` | GitLab instance URL (self-hosted supported) |

### AWS

| Variable | Default | Description |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | *(none)* | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | *(none)* | AWS secret key |
| `AWS_REGION` | `us-east-1` | Default region |

### Kubernetes

| Variable | Description |
|---|---|
| `KUBECONFIG` | Path to kubeconfig file |

### Terraform

| Variable | Default | Description |
|---|---|---|
| `TERRAFORM_BINARY` | `terraform` | Path to terraform binary |
| `TERRAFORM_ALLOWED_BASE_DIR` | `/tmp/terraform` | Sandbox root for all Terraform paths |
| `TERRAFORM_TIMEOUT_SECONDS` | `600` | Max seconds per command |

### Helm

| Variable | Default | Description |
|---|---|---|
| `HELM_BINARY` | `helm` | Path to helm binary |
| `HELM_TIMEOUT_SECONDS` | `300` | Max seconds per command |

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
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON key |

### ArgoCD

| Variable | Default | Description |
|---|---|---|
| `ARGOCD_SERVER_URL` | *(none)* | ArgoCD server URL |
| `ARGOCD_AUTH_TOKEN` | *(none)* | ArgoCD API token |
| `ARGOCD_INSECURE` | `false` | Skip TLS verification |

### HashiCorp Vault

| Variable | Default | Description |
|---|---|---|
| `VAULT_ADDR` | *(none)* | Vault server address |
| `VAULT_TOKEN` | *(none)* | Vault token |
| `VAULT_NAMESPACE` | *(none)* | Vault namespace (Enterprise) |
| `VAULT_MOUNT` | `secret` | KV v2 mount path |

### PagerDuty

| Variable | Description |
|---|---|
| `PAGERDUTY_API_KEY` | PagerDuty REST API v2 key |
| `PAGERDUTY_EMAIL` | From email for incident creation |
| `PAGERDUTY_SERVICE_ID` | Default service ID for new incidents |

### Datadog

| Variable | Default | Description |
|---|---|---|
| `DATADOG_API_KEY` | *(none)* | Datadog API key |
| `DATADOG_APP_KEY` | *(none)* | Datadog application key |
| `DATADOG_SITE` | `datadoghq.com` | Datadog site (`datadoghq.eu` for EU) |

### Docker

| Variable | Default | Description |
|---|---|---|
| `DOCKER_BINARY` | `docker` | Path to docker binary |
| `DOCKER_TIMEOUT_SECONDS` | `300` | Max seconds per command |

### Jenkins

| Variable | Description |
|---|---|
| `JENKINS_URL` | Jenkins server URL |
| `JENKINS_USER` | Jenkins username |
| `JENKINS_TOKEN` | Jenkins API token |

### Cloudflare

| Variable | Description |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account ID |

### Ansible

| Variable | Default | Description |
|---|---|---|
| `ANSIBLE_BINARY` | `ansible` | Path to ansible binary |
| `ANSIBLE_PLAYBOOK_BINARY` | `ansible-playbook` | Path to ansible-playbook binary |
| `ANSIBLE_TIMEOUT_SECONDS` | `600` | Max seconds per command |

### Security Scanners

| Variable | Default | Description |
|---|---|---|
| `TRIVY_BINARY` | `trivy` | Path to trivy binary |
| `TFSEC_BINARY` | `tfsec` | Path to tfsec binary |
| `SCANNER_TIMEOUT_SECONDS` | `120` | Max seconds per scan |

### Infracost

| Variable | Description |
|---|---|
| `INFRACOST_API_KEY` | Infracost API key |
| `INFRACOST_BINARY` | Path to infracost binary (default: `infracost`) |

### Slack (optional)

| Variable | Description |
|---|---|
| `SLACK_WEBHOOK_URL` | Incoming webhook for tool notifications |

---

## Running the Server

### HTTP mode

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
| `GET` | `/tools` | List all 160 tools |
| `GET` | `/tools?tag=aws` | Filter tools by tag |
| `GET` | `/tools/{name}` | Describe one tool |
| `POST` | `/tools/execute` | Execute a tool |
| `POST` | `/tools/batch` | Execute multiple tools |
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
        "GITLAB_TOKEN": "glpat-...",
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
        "DATADOG_API_KEY": "...",
        "DATADOG_APP_KEY": "...",
        "JENKINS_URL": "https://jenkins.example.com",
        "JENKINS_USER": "admin",
        "JENKINS_TOKEN": "...",
        "CLOUDFLARE_API_TOKEN": "...",
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
docker build -t devops-mcp-server .
docker run --env-file .env -p 8000:8000 devops-mcp-server
# or
docker-compose up
```

---

## Tool Reference

### Terraform Tools

| Tool | Description |
|---|---|
| `terraform_plan` | Run `terraform plan` — returns the plan output |
| `terraform_apply` | Run `terraform apply -auto-approve` |
| `terraform_destroy` | Run `terraform destroy -auto-approve` (destructive) |
| `terraform_init` | Run `terraform init` to initialize providers |
| `terraform_validate` | Validate configuration syntax |
| `terraform_output` | Get output values as JSON |
| `terraform_state_list` | List all managed resources |

---

### GitHub Tools

| Tool | Description |
|---|---|
| `github_create_pull_request` | Create a pull request |
| `github_get_repo` | Get repository metadata |
| `github_list_issues` | List open issues |
| `github_trigger_workflow` | Trigger a workflow dispatch event |
| `github_create_release` | Create a tagged release |
| `github_create_issue` | Create a new issue |
| `github_merge_pull_request` | Merge an open pull request |
| `github_get_workflow_run` | Get workflow run status |

**Required env:** `GITHUB_TOKEN`

---

### GitLab Tools

| Tool | Description |
|---|---|
| `gitlab_list_projects` | List accessible projects |
| `gitlab_list_merge_requests` | List MRs by state (opened/merged/closed) |
| `gitlab_create_merge_request` | Create a merge request |
| `gitlab_merge_mr` | Merge an open MR |
| `gitlab_list_pipelines` | List CI/CD pipelines |
| `gitlab_trigger_pipeline` | Trigger a pipeline on a ref |
| `gitlab_list_issues` | List project issues |

**Required env:** `GITLAB_TOKEN`, `GITLAB_URL`

---

### AWS Tools

#### EC2

| Tool | Description |
|---|---|
| `aws_describe_ec2_instance` | Describe an EC2 instance |
| `aws_list_ec2_instances` | List EC2 instances |
| `aws_stop_ec2_instance` | Stop an instance |
| `aws_start_ec2_instance` | Start an instance |
| `aws_terminate_ec2_instance` | Terminate an instance (destructive) |

#### S3

| Tool | Description |
|---|---|
| `aws_list_s3_buckets` | List all S3 buckets |
| `aws_create_s3_bucket` | Create a bucket |
| `aws_list_s3_objects` | List objects with prefix filter |
| `aws_upload_s3_object` | Upload text content to an object |

#### Lambda

| Tool | Description |
|---|---|
| `aws_list_lambda_functions` | List Lambda functions |
| `aws_invoke_lambda` | Invoke a Lambda synchronously |

#### RDS

| Tool | Description |
|---|---|
| `aws_list_rds_instances` | List RDS instances |
| `aws_rds_create_instance` | Create an RDS instance |
| `aws_rds_create_snapshot` | Create a snapshot |
| `aws_rds_restore_from_snapshot` | Restore from snapshot |

#### CloudWatch

| Tool | Description |
|---|---|
| `aws_cloudwatch_get_metrics` | Get metric statistics |
| `aws_cloudwatch_list_alarms` | List alarms |
| `aws_cloudwatch_list_log_groups` | List log groups |
| `aws_cloudwatch_query_logs` | Run a Logs Insights query |

#### Secrets Manager & SSM

| Tool | Description |
|---|---|
| `aws_secrets_get` | Get a secret value |
| `aws_secrets_create` | Create a secret |
| `aws_ssm_get_parameter` | Get an SSM parameter |
| `aws_ssm_put_parameter` | Put an SSM parameter |

#### Networking

| Tool | Description |
|---|---|
| `aws_list_vpcs` | List VPCs |
| `aws_list_security_groups` | List security groups |
| `aws_list_route53_zones` | List Route 53 hosted zones |

#### IAM

| Tool | Description |
|---|---|
| `aws_iam_list_roles` | List IAM roles |
| `aws_iam_list_policies` | List customer-managed policies |
| `aws_iam_simulate_policy` | Simulate policy evaluation |

#### ECS

| Tool | Description |
|---|---|
| `aws_ecs_list_clusters` | List ECS clusters |
| `aws_ecs_list_services` | List services in a cluster |
| `aws_ecs_list_tasks` | List running tasks |
| `aws_ecs_deploy_service` | Force a new deployment |

#### ECR

| Tool | Description |
|---|---|
| `aws_ecr_list_repositories` | List ECR repositories |
| `aws_ecr_list_images` | List images in a repository |

#### ALB

| Tool | Description |
|---|---|
| `aws_alb_list` | List load balancers |
| `aws_alb_list_target_groups` | List target groups |

#### SQS

| Tool | Description |
|---|---|
| `aws_sqs_list_queues` | List SQS queues |
| `aws_sqs_send_message` | Send a message to a queue |
| `aws_sqs_get_queue_attributes` | Get queue depth and attributes |
| `aws_sqs_purge_queue` | Purge all messages (destructive) |

#### SNS

| Tool | Description |
|---|---|
| `aws_sns_list_topics` | List SNS topics |
| `aws_sns_publish` | Publish a message to a topic |
| `aws_sns_list_subscriptions` | List subscriptions |

#### DynamoDB

| Tool | Description |
|---|---|
| `aws_dynamodb_list_tables` | List DynamoDB tables |
| `aws_dynamodb_describe_table` | Describe a table |
| `aws_dynamodb_get_item` | Get an item by primary key |
| `aws_dynamodb_put_item` | Create or replace an item |

#### Cost Explorer

| Tool | Description |
|---|---|
| `aws_cost_by_service` | Get cost breakdown by service |
| `aws_cost_monthly_total` | Get total monthly spend |

**Required env:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`

---

### Kubernetes Tools

| Tool | Description |
|---|---|
| `k8s_deploy` | Deploy or update a deployment image |
| `k8s_get_pods` | List pods in a namespace |
| `k8s_get_logs` | Get pod container logs |
| `k8s_get_events` | Get namespace events |
| `k8s_scale` | Scale a deployment |
| `k8s_rollout_restart` | Rolling restart a deployment |
| `k8s_rollout_status` | Check rollout status |
| `k8s_get_deployments` | List deployments |
| `k8s_get_services` | List services |
| `k8s_get_nodes` | List cluster nodes |
| `k8s_delete_pod` | Delete a pod |
| `kubernetes_list_namespaces` | List namespaces |
| `kubernetes_create_namespace` | Create a namespace |
| `kubernetes_get_configmap` | Get a ConfigMap |
| `kubernetes_apply_configmap` | Create or update a ConfigMap |
| `kubernetes_list_secrets` | List secret names (keys only) |
| `kubernetes_list_jobs` | List Jobs |
| `kubernetes_list_cronjobs` | List CronJobs |
| `kubernetes_list_ingresses` | List Ingress resources |

**Required env:** `KUBECONFIG`

---

### Helm Tools

| Tool | Description |
|---|---|
| `helm_list` | List Helm releases |
| `helm_install` | Install a chart |
| `helm_upgrade` | Upgrade a release |
| `helm_rollback` | Roll back to a previous revision |
| `helm_status` | Get release status |

**Required env:** `HELM_BINARY`, `KUBECONFIG`

---

### Azure Tools

| Tool | Description |
|---|---|
| `azure_list_resource_groups` | List resource groups |
| `azure_list_vms` | List VMs in a resource group |
| `azure_start_vm` | Start a VM |
| `azure_stop_vm` | Deallocate a VM |
| `azure_aks_list_clusters` | List AKS clusters |
| `azure_list_acr_registries` | List container registries |
| `azure_keyvault_get_secret` | Get a Key Vault secret |
| `azure_keyvault_set_secret` | Set a Key Vault secret |

**Required env:** `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`

---

### GCP Tools

| Tool | Description |
|---|---|
| `gcp_list_instances` | List Compute Engine instances |
| `gcp_list_buckets` | List Cloud Storage buckets |
| `gcp_list_gke_clusters` | List GKE clusters |
| `gcp_cloudrun_list_services` | List Cloud Run services |
| `gcp_cloudsql_list_instances` | List Cloud SQL instances |
| `gcp_cloudbuild_list_builds` | List recent Cloud Build builds |
| `gcp_cloudbuild_trigger` | Trigger a Cloud Build |

**Required env:** `GCP_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`

---

### ArgoCD Tools

| Tool | Description |
|---|---|
| `argocd_list_apps` | List applications with sync status |
| `argocd_get_app` | Get detailed app status |
| `argocd_sync_app` | Trigger a sync |
| `argocd_rollback_app` | Roll back to a previous revision |

**Required env:** `ARGOCD_SERVER_URL`, `ARGOCD_AUTH_TOKEN`

---

### HashiCorp Vault Tools

| Tool | Description |
|---|---|
| `vault_read_secret` | Read a KV v2 secret |
| `vault_write_secret` | Write to KV v2 |
| `vault_list_secrets` | List keys at a path |

**Required env:** `VAULT_ADDR`, `VAULT_TOKEN`

---

### PagerDuty Tools

| Tool | Description |
|---|---|
| `pagerduty_list_incidents` | List incidents by status |
| `pagerduty_acknowledge_incident` | Acknowledge an incident |
| `pagerduty_resolve_incident` | Resolve an incident |
| `pagerduty_create_incident` | Create a new incident |

**Required env:** `PAGERDUTY_API_KEY`, `PAGERDUTY_EMAIL`

---

### Datadog Tools

| Tool | Description |
|---|---|
| `datadog_list_monitors` | List monitors with current status |
| `datadog_mute_monitor` | Mute a monitor |
| `datadog_unmute_monitor` | Unmute a monitor |
| `datadog_query_metrics` | Query time-series metrics |
| `datadog_list_events` | List events from the event stream |
| `datadog_create_event` | Post a custom event (deployments, etc.) |
| `datadog_list_dashboards` | List dashboards |
| `datadog_list_incidents` | List active incidents |
| `datadog_list_hosts` | List reporting hosts |

**Required env:** `DATADOG_API_KEY`, `DATADOG_APP_KEY`

---

### Docker Tools

| Tool | Description |
|---|---|
| `docker_list_images` | List local Docker images |
| `docker_pull` | Pull an image from a registry |
| `docker_build` | Build an image from a Dockerfile |
| `docker_push` | Push an image to a registry |
| `docker_inspect` | Inspect image metadata |
| `docker_list_containers` | List running (or all) containers |
| `docker_logs` | Get container log output |
| `docker_tag` | Tag an image with a new name |

**Required:** `docker` binary on PATH

---

### Jenkins Tools

| Tool | Description |
|---|---|
| `jenkins_list_jobs` | List all jobs with status |
| `jenkins_get_job` | Get job details and build history |
| `jenkins_trigger_build` | Trigger a build (with optional params) |
| `jenkins_get_build` | Get build result and duration |
| `jenkins_get_build_log` | Get console output for a build |
| `jenkins_list_builds` | List recent builds for a job |

**Required env:** `JENKINS_URL`, `JENKINS_USER`, `JENKINS_TOKEN`

---

### Cloudflare Tools

| Tool | Description |
|---|---|
| `cloudflare_list_zones` | List zones (domains) |
| `cloudflare_list_dns_records` | List DNS records in a zone |
| `cloudflare_create_dns_record` | Create a DNS record |
| `cloudflare_delete_dns_record` | Delete a DNS record |
| `cloudflare_purge_cache` | Purge zone cache (all or specific URLs) |
| `cloudflare_list_waf_rules` | List WAF firewall rules |

**Required env:** `CLOUDFLARE_API_TOKEN`

---

### Ansible Tools

| Tool | Description |
|---|---|
| `ansible_run_playbook` | Run an Ansible playbook |
| `ansible_list_hosts` | List hosts matching a pattern |
| `ansible_ping` | Ping hosts to verify connectivity |
| `ansible_run_module` | Run an ad-hoc Ansible module |

**Required:** `ansible` and `ansible-playbook` binaries on PATH

---

### Security Scanning Tools

| Tool | Description |
|---|---|
| `trivy_scan_image` | Scan a Docker image for CVEs |
| `trivy_scan_filesystem` | Scan a directory for dependency vulnerabilities |
| `tfsec_scan` | Scan Terraform code for misconfigurations |

**Required:** `trivy` and `tfsec` binaries on PATH

---

### GCP Secret Manager Tools

| Tool | Description |
|---|---|
| `gcp_secret_manager_list` | List secrets (names only) |
| `gcp_secret_manager_get` | Get a secret value by ID |
| `gcp_secret_manager_create` | Create a new secret |

**Required env:** `GCP_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`

---

### Multi-cloud FinOps Tools

| Tool | Description |
|---|---|
| `azure_cost_by_service` | Azure spend breakdown by service |
| `gcp_billing_monthly_spend` | GCP monthly spend via BigQuery billing export |
| `infracost_estimate` | Estimate Terraform plan cost with Infracost |

---

## Tool Summary

| Service | Tools | Tags |
|---|---|---|
| Terraform | 7 | `terraform`, `iac` |
| GitHub | 8 | `github`, `scm` |
| GitLab | 7 | `gitlab`, `scm`, `ci` |
| AWS EC2 | 5 | `aws`, `ec2`, `compute` |
| AWS S3 | 4 | `aws`, `s3`, `storage` |
| AWS Lambda | 2 | `aws`, `lambda`, `serverless` |
| AWS RDS | 4 | `aws`, `rds`, `database` |
| AWS CloudWatch | 4 | `aws`, `cloudwatch`, `observability` |
| AWS Secrets/SSM | 4 | `aws`, `secrets`, `ssm` |
| AWS Networking | 3 | `aws`, `networking` |
| AWS IAM | 3 | `aws`, `iam`, `security` |
| AWS ECS | 4 | `aws`, `ecs`, `compute` |
| AWS ECR | 2 | `aws`, `ecr`, `containers` |
| AWS ALB | 2 | `aws`, `networking`, `alb` |
| AWS SQS | 4 | `aws`, `sqs`, `messaging` |
| AWS SNS | 3 | `aws`, `sns`, `messaging` |
| AWS DynamoDB | 4 | `aws`, `dynamodb`, `database` |
| AWS Cost Explorer | 2 | `aws`, `cost`, `finops` |
| Kubernetes | 19 | `kubernetes`, `k8s` |
| Helm | 5 | `helm`, `kubernetes` |
| Azure | 8 | `azure`, `multicloud` |
| GCP | 7 | `gcp`, `multicloud` |
| GCP Secret Manager | 3 | `gcp`, `secrets` |
| ArgoCD | 4 | `argocd`, `gitops` |
| HashiCorp Vault | 3 | `vault`, `secrets` |
| PagerDuty | 4 | `pagerduty`, `incident` |
| Datadog | 9 | `datadog`, `observability` |
| Docker | 8 | `docker`, `containers` |
| Jenkins | 6 | `jenkins`, `ci` |
| Cloudflare | 6 | `cloudflare`, `dns` |
| Ansible | 4 | `ansible`, `automation` |
| Security Scanning | 3 | `security`, `trivy`, `tfsec` |
| Multi-cloud FinOps | 3 | `finops`, `cost` |
| **Total** | **160** | |

---

## Example Workflows

### Incident response (full end-to-end)

```python
# 1. Get alerted
incidents = execute_tool("pagerduty_list_incidents", {"status": "triggered"})
execute_tool("pagerduty_acknowledge_incident", {"incident_id": "P1234AB"})

# 2. Check Datadog — what's firing?
execute_tool("datadog_list_monitors", {"status": "Alert"})
execute_tool("datadog_query_metrics", {"query": "avg:system.cpu.user{env:prod}", "minutes": 30})

# 3. Pull CloudWatch logs
execute_tool("aws_cloudwatch_query_logs", {
    "log_group": "/aws/ecs/api",
    "query": "fields @message | filter @message like /ERROR/ | limit 20",
    "minutes": 15
})

# 4. Check K8s pods
execute_tool("k8s_get_pods", {"namespace": "production"})

# 5. Rolling restart to clear bad state
execute_tool("k8s_rollout_restart", {"deployment": "api", "namespace": "production"})

# 6. Mark deployment event in Datadog
execute_tool("datadog_create_event", {
    "title": "Rollout restart — api", "text": "Auto-restarted by AI agent",
    "tags": ["env:prod", "service:api"]
})

# 7. Resolve
execute_tool("pagerduty_resolve_incident", {"incident_id": "P1234AB"})
```

### Full CI/CD release pipeline

```python
# 1. Trigger Jenkins build
execute_tool("jenkins_trigger_build", {"job_name": "api-build", "params": {"VERSION": "v2.1.0"}})

# 2. Watch build log
execute_tool("jenkins_get_build_log", {"job_name": "api-build", "build_number": 42})

# 3. Scan image for CVEs before shipping
execute_tool("trivy_scan_image", {"image": "myrepo/api:v2.1.0", "severity": "HIGH,CRITICAL"})

# 4. Push to ECR
execute_tool("docker_push", {"image": "123456789.dkr.ecr.us-east-1.amazonaws.com/api:v2.1.0"})

# 5. Scan Terraform before apply
execute_tool("tfsec_scan", {"path": "/infra/prod"})
execute_tool("infracost_estimate", {"path": "/infra/prod"})
execute_tool("terraform_apply", {"working_dir": "/infra/prod"})

# 6. Deploy via Helm
execute_tool("helm_upgrade", {
    "release": "api", "chart": "myrepo/api",
    "namespace": "production", "values": {"image.tag": "v2.1.0"}
})

# 7. Sync ArgoCD
execute_tool("argocd_sync_app", {"app_name": "api-production"})

# 8. Create GitHub release
execute_tool("github_create_release", {
    "owner": "my-org", "repo": "api", "tag": "v2.1.0", "name": "v2.1.0"
})

# 9. Purge Cloudflare cache
execute_tool("cloudflare_purge_cache", {"zone_id": "abc123"})
```

### Multi-cloud cost review

```python
# AWS
execute_tool("aws_cost_by_service", {"start_date": "2026-04-01", "end_date": "2026-04-22"})

# Azure
execute_tool("azure_cost_by_service", {"start_date": "2026-04-01", "end_date": "2026-04-22"})

# GCP
execute_tool("gcp_billing_monthly_spend", {"dataset": "billing", "table": "gcp_billing_export_v1_XXXX"})

# Estimate next Terraform change
execute_tool("infracost_estimate", {"path": "/infra/aws"})
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

No other files need to change.

---

## Running Tests

```bash
pip install pytest pytest-asyncio pytest-mock
pytest tests/ -v
# 152 tests, all pass
```

---

## Security Model

- **API key auth**: Set `MCP_API_KEY` — all requests require `Authorization: Bearer <key>` or `X-API-Key: <key>`.
- **Terraform sandboxing**: All paths validated against `TERRAFORM_ALLOWED_BASE_DIR`. Path traversal blocked.
- **No shell=True**: All subprocess calls (Terraform, Helm, Docker, Ansible, Trivy, tfsec, Infracost) use argument lists.
- **K8s secrets**: `kubernetes_list_secrets` returns key names only — values never returned.
- **Audit log**: Every tool execution is logged to SQLite (name, inputs hash, status, duration).
- **DRY_RUN mode**: Set `DRY_RUN=true` to block all mutating operations.
- **Destructive tag**: Tools tagged `destructive` are clearly labelled — add confirmation logic in your agent if needed.
- **CORS**: Set `CORS_ORIGINS` to explicit origins in production.

---

## Troubleshooting

### Check how many tools are registered

```bash
curl http://localhost:8000/tools | python -m json.tool | grep '"count"'
# Should be 160
```

### AWS authentication errors

```bash
aws sts get-caller-identity
```

### Kubernetes connection refused

```bash
kubectl cluster-info
```

### Azure authentication errors

Verify all four env vars: `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`.

### Datadog 403 errors

Confirm both `DATADOG_API_KEY` and `DATADOG_APP_KEY` are set — the app key is required for read operations.

### Jenkins 401 errors

Use an API token, not your password. Generate one at `<jenkins-url>/user/<username>/configure`.

### Cloudflare API errors

Ensure your API token has the correct permissions for the zone (DNS Edit, Cache Purge, Firewall Rules Read).

### Docker / Ansible / Trivy / tfsec not found

These use CLI subprocess calls. Ensure the binary is installed and on your `PATH`:

```bash
which docker ansible trivy tfsec infracost helm terraform
```

### Terraform timeout

Increase `TERRAFORM_TIMEOUT_SECONDS` (default 600). Large state files may need 900–1800s.

---

## License

MIT — see [LICENSE](LICENSE).
