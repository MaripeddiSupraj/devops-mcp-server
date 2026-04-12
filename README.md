# DevOps MCP Server

> A **production-grade Model Context Protocol (MCP) server** that exposes Terraform, GitHub, AWS, and Kubernetes as structured JSON tool APIs — designed for AI agents (LangGraph, AutoGen, custom agents) to automate DevOps workflows end-to-end.

---

## Table of Contents

- [What is This?](#what-is-this)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [Docker](#docker)
- [API Reference](#api-reference)
- [Tool Reference](#tool-reference)
  - [Terraform Tools](#terraform-tools)
  - [GitHub Tools](#github-tools)
  - [AWS Tools](#aws-tools)
  - [Kubernetes Tools](#kubernetes-tools)
- [Example Workflows](#example-workflows)
- [Adding a New Tool](#adding-a-new-tool)
- [Running Tests](#running-tests)
- [Security Model](#security-model)
- [Troubleshooting](#troubleshooting)

---

## What is This?

This server implements the [Model Context Protocol](https://modelcontextprotocol.io) — a standard that lets AI agents discover and invoke tools over HTTP. Instead of hard-coding API calls into your AI agent, you point it at this server and it dynamically discovers what DevOps operations are available.

**Without MCP:**

```text
Agent → custom boto3 code → AWS
Agent → custom subprocess → Terraform
Agent → custom PyGithub code → GitHub
```

**With MCP:**

```text
Agent → POST /tools/execute → MCP Server → AWS / Terraform / GitHub / Kubernetes
```

The agent calls one endpoint with a tool name and JSON inputs. The server handles all SDK complexity, authentication, validation, and error formatting.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                        AI Agent                             │
│         (LangGraph / AutoGen / custom agent)                │
└───────────────────────────┬─────────────────────────────────┘
                            │ POST /tools/execute
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI MCP Server                        │
│                                                             │
│   GET /tools          →  ToolRegistry (list all tools)      │
│   POST /tools/execute →  ToolExecutor (validate + run)      │
│   GET /tools/{name}   →  ToolRegistry (describe one tool)   │
└──────────┬──────────────────────────────────────────────────┘
           │
    ┌──────┴───────────────────────────────────────┐
    │              Tool Handlers                    │
    │  terraform/  github/  aws/  kubernetes/       │
    └──────┬───────────────────────────────────────┘
           │
    ┌──────┴───────────────────────────────────────┐
    │              Integrations                     │
    │  subprocess  PyGithub  boto3  k8s-client      │
    └──────────────────────────────────────────────┘
```

**Request lifecycle:**
1. Agent sends `POST /tools/execute` with `tool_name` and `inputs`
2. `ToolExecutor` validates inputs against the tool's JSON schema
3. Handler function is resolved from `ToolRegistry`
4. Handler calls the appropriate integration (boto3, PyGithub, etc.)
5. Result wrapped in `{"status": "success"|"error", "data": ..., "error": ...}`

---

## Project Structure

```text
devops_mcp/
│
├── server/
│   ├── main.py          # FastAPI app — all HTTP routes
│   ├── registry.py      # Tool registration + build_registry()
│   └── schemas.py       # Pydantic models for request/response
│
├── tools/               # One file per tool (metadata + handler)
│   ├── terraform/
│   │   ├── plan.py
│   │   ├── apply.py
│   │   └── destroy.py
│   ├── github/
│   │   ├── create_pr.py
│   │   └── get_repo.py
│   ├── aws/
│   │   ├── ec2.py
│   │   └── s3.py
│   └── kubernetes/
│       ├── deploy.py
│       ├── get_pods.py
│       ├── get_logs.py
│       ├── get_events.py
│       ├── scale.py
│       ├── rollout_restart.py
│       ├── rollout_status.py
│       ├── get_deployments.py
│       ├── get_services.py
│       ├── get_nodes.py
│       └── delete_pod.py
│
├── core/
│   ├── config.py        # Pydantic-settings (env vars)
│   ├── logger.py        # Structured JSON logging (structlog)
│   ├── auth.py          # Credential helpers
│   └── executor.py      # Schema validation + execution engine
│
├── integrations/
│   ├── terraform_runner.py  # subprocess wrapper (no shell=True)
│   ├── github_client.py     # PyGithub wrapper
│   ├── aws_client.py        # boto3 EC2 + S3
│   └── k8s_client.py        # kubernetes-client wrapper
│
├── tests/
│   ├── conftest.py
│   ├── test_registry.py
│   ├── test_executor.py
│   ├── test_api.py
│   └── test_terraform_runner.py
│
├── .env.example
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/devops-mcp-server.git
cd devops_mcp

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
KUBECONFIG=/Users/yourname/.kube/config
TERRAFORM_ALLOWED_BASE_DIR=/tmp/terraform
```

### 3. Start the server

```bash
python -m server.main
```

### 4. Verify it's running

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"1.0.0","tools_registered":20}
```

### 5. List all tools

```bash
curl http://localhost:8000/tools | python -m json.tool
```

---

## Configuration

All configuration is via environment variables (or `.env` file).

| Variable | Default | Description |
| --- | --- | --- |
| `GITHUB_TOKEN` | — | GitHub Personal Access Token (`repo` + `workflow` scopes) |
| `AWS_ACCESS_KEY_ID` | — | AWS IAM access key |
| `AWS_SECRET_ACCESS_KEY` | — | AWS IAM secret key |
| `AWS_REGION` | `us-east-1` | Default AWS region |
| `KUBECONFIG` | in-cluster | Path to kubeconfig (omit for in-cluster SA token) |
| `TERRAFORM_BINARY` | `terraform` | Path to Terraform binary |
| `TERRAFORM_ALLOWED_BASE_DIR` | `/tmp/terraform` | **Security**: all Terraform paths must be under this root |
| `SERVER_HOST` | `0.0.0.0` | Server bind address |
| `SERVER_PORT` | `8000` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `DRY_RUN` | `false` | **Safety**: `true` disables all destructive operations globally |

---

## Running the Server

### Development

```bash
python -m server.main
```

### Production (multi-worker)

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Interactive API docs

| URL | Description |
| --- | --- |
| `http://localhost:8000/docs` | Swagger UI — try tools interactively |
| `http://localhost:8000/redoc` | ReDoc — clean reference docs |

---

## Docker

### Build

```bash
docker build -t devops-mcp-server:latest .
```

### Run

```bash
docker run -d \
  --name devops-mcp \
  -p 8000:8000 \
  -e GITHUB_TOKEN=ghp_xxx \
  -e AWS_ACCESS_KEY_ID=AKIA... \
  -e AWS_SECRET_ACCESS_KEY=... \
  -e AWS_REGION=us-east-1 \
  -e KUBECONFIG=/kubeconfig \
  -v ~/.kube/config:/kubeconfig:ro \
  -e DRY_RUN=false \
  devops-mcp-server:latest
```

### Health check

```bash
docker inspect --format='{{json .State.Health}}' devops-mcp
```

---

## API Reference

### `GET /health`

Liveness probe.

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "version": "1.0.0",
  "tools_registered": 20
}
```

---

### `GET /tools`

List all registered tools with their schemas.

```bash
curl http://localhost:8000/tools
```

```json
{
  "count": 20,
  "tools": [
    {
      "name": "terraform_plan",
      "description": "Runs terraform plan in the specified directory...",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": { "type": "string" },
          "dry_run": { "type": "boolean", "default": false }
        },
        "required": ["path"]
      }
    },
    ...
  ]
}
```

---

### `GET /tools/{tool_name}`

Describe a single tool.

```bash
curl http://localhost:8000/tools/k8s_get_logs
```

```json
{
  "name": "k8s_get_logs",
  "description": "Fetches logs from a Kubernetes pod container...",
  "input_schema": { ... }
}
```

---

### `POST /tools/execute`

Execute any tool. This is the primary endpoint used by AI agents.

**Request:**

```json
{
  "tool_name": "<registered_tool_name>",
  "inputs": {
    "<param>": "<value>"
  }
}
```

**Response (always the same envelope):**

```json
{
  "status": "success",
  "data": { ... },
  "error": null
}
```

or on error:

```json
{
  "status": "error",
  "data": null,
  "error": "Human-readable description of what went wrong"
}
```

> The HTTP status code is always `200`. Check `response.status` in the body to determine success or failure.

---

## Tool Reference

### Terraform Tools

#### `terraform_plan`

Runs `terraform plan` and returns stdout, stderr, exit code, and a `has_changes` boolean.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `path` | string | Yes | — | Absolute path to Terraform working directory |
| `dry_run` | boolean | No | `false` | Run `terraform validate` instead of a real plan |

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "terraform_plan",
    "inputs": {
      "path": "/tmp/terraform/my-infra"
    }
  }' | python -m json.tool
```

```json
{
  "status": "success",
  "data": {
    "stdout": "Plan: 3 to add, 1 to change, 0 to destroy.",
    "stderr": "",
    "exit_code": 2,
    "has_changes": true,
    "dry_run": false
  }
}
```

> `exit_code` meanings: `0` = no changes, `2` = changes present, other = error.

---

#### `terraform_apply`

Applies the Terraform configuration. **Blocked when `DRY_RUN=true`.**

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `path` | string | Yes | — | Terraform working directory |
| `auto_approve` | boolean | No | `false` | Skip interactive approval prompt |

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "terraform_apply",
    "inputs": {
      "path": "/tmp/terraform/my-infra",
      "auto_approve": true
    }
  }'
```

---

#### `terraform_destroy`

Destroys all resources. **Requires explicit confirmation string.**

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `path` | string | Yes | — | Terraform working directory |
| `confirm_destroy` | string | Yes | — | Must be exactly `"DESTROY"` |
| `auto_approve` | boolean | No | `false` | Skip interactive prompt |

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "terraform_destroy",
    "inputs": {
      "path": "/tmp/terraform/my-infra",
      "confirm_destroy": "DESTROY",
      "auto_approve": true
    }
  }'
```

---

### GitHub Tools

#### `github_create_pull_request`

Opens a pull request. Requires `GITHUB_TOKEN` with `repo` scope.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `repo` | string | Yes | — | `owner/repo` format |
| `title` | string | Yes | — | PR title |
| `body` | string | Yes | — | PR description (Markdown) |
| `head` | string | Yes | — | Source branch to merge from |
| `base` | string | No | `main` | Target branch to merge into |
| `draft` | boolean | No | `false` | Create as draft PR |

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "github_create_pull_request",
    "inputs": {
      "repo": "myorg/myapp",
      "title": "feat: add Redis caching layer",
      "body": "## Summary\n- Added Redis client\n- Implemented cache-aside pattern\n\n## Test Plan\n- [x] Unit tests\n- [x] Integration tests",
      "head": "feature/redis-cache",
      "base": "main"
    }
  }'
```

```json
{
  "status": "success",
  "data": {
    "number": 47,
    "url": "https://github.com/myorg/myapp/pull/47",
    "state": "open",
    "title": "feat: add Redis caching layer",
    "head": "feature/redis-cache",
    "base": "main"
  }
}
```

---

#### `github_get_repo`

Fetches repository metadata.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `repo` | string | Yes | `owner/repo` format |

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "github_get_repo", "inputs": {"repo": "kubernetes/kubernetes"}}'
```

```json
{
  "status": "success",
  "data": {
    "name": "kubernetes",
    "full_name": "kubernetes/kubernetes",
    "description": "Production-Grade Container Scheduling and Management",
    "url": "https://github.com/kubernetes/kubernetes",
    "default_branch": "master",
    "stars": 108000,
    "forks": 38500,
    "open_issues": 2400,
    "private": false,
    "language": "Go"
  }
}
```

---

### AWS Tools

#### `aws_create_ec2_instance`

Launches an EC2 instance. Instance type must be in the allowed list.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | string | Yes | — | Value for the `Name` tag |
| `instance_type` | string | Yes | — | Must be in allowlist (see below) |
| `ami_id` | string | Yes | — | Amazon Machine Image ID |
| `key_name` | string | No | — | EC2 Key Pair for SSH access |
| `subnet_id` | string | No | — | VPC Subnet ID |
| `security_group_ids` | array | No | — | List of Security Group IDs |
| `dry_run` | boolean | No | `false` | Validate permissions only |

**Allowed instance types:** `t2.micro`, `t2.small`, `t2.medium`, `t3.micro`, `t3.small`, `t3.medium`, `t3.large`, `t3a.micro`, `t3a.small`, `t3a.medium`, `m5.large`, `m5.xlarge`, `c5.large`, `c5.xlarge`

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "aws_create_ec2_instance",
    "inputs": {
      "name": "web-server-prod-01",
      "instance_type": "t3.medium",
      "ami_id": "ami-0c55b159cbfafe1f0",
      "key_name": "my-keypair",
      "security_group_ids": ["sg-0abc123def456789"]
    }
  }'
```

```json
{
  "status": "success",
  "data": {
    "instance_id": "i-0abc123def456789a",
    "state": "pending",
    "instance_type": "t3.medium",
    "ami": "ami-0c55b159cbfafe1f0",
    "availability_zone": "us-east-1a"
  }
}
```

---

#### `aws_list_ec2_instances`

Lists EC2 instances with optional state filter.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `state` | string | No | Filter: `running`, `stopped`, `pending`, etc. |

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "aws_list_ec2_instances", "inputs": {"state": "running"}}'
```

---

#### `aws_create_s3_bucket`

Creates an S3 bucket with all public access blocked by default.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `bucket_name` | string | Yes | Globally unique, 3-63 lowercase chars |
| `region` | string | No | AWS region (defaults to `AWS_REGION`) |

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "aws_create_s3_bucket",
    "inputs": {
      "bucket_name": "myapp-artifacts-prod-2024",
      "region": "us-west-2"
    }
  }'
```

```json
{
  "status": "success",
  "data": {
    "bucket": "myapp-artifacts-prod-2024",
    "region": "us-west-2",
    "public_access": "blocked"
  }
}
```

---

#### `aws_list_s3_buckets`

Lists all S3 buckets in the account. No inputs required.

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "aws_list_s3_buckets", "inputs": {}}'
```

---

### Kubernetes Tools

> All Kubernetes tools default to the `default` namespace. Pass `"namespace": "production"` (or any namespace) to override.

---

#### `k8s_get_pods`

Lists all pods in a namespace with readiness, restart count, node, and IP.

| Parameter | Type | Required | Default |
| --- | --- | --- | --- |
| `namespace` | string | No | `default` |

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "k8s_get_pods", "inputs": {"namespace": "production"}}'
```

```json
{
  "status": "success",
  "data": [
    {
      "name": "api-server-7d9f6b8c4-xk2pn",
      "namespace": "production",
      "status": "Running",
      "ready": true,
      "restarts": 0,
      "node": "ip-10-0-1-42.ec2.internal",
      "ip": "10.244.3.15"
    },
    {
      "name": "worker-6c8b5d7f9-mq4rs",
      "namespace": "production",
      "status": "CrashLoopBackOff",
      "ready": false,
      "restarts": 7,
      "node": "ip-10-0-1-43.ec2.internal",
      "ip": "10.244.3.21"
    }
  ]
}
```

---

#### `k8s_get_logs`

Fetches pod logs. The most-used debugging tool in Kubernetes.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `pod_name` | string | Yes | — | Exact pod name |
| `namespace` | string | No | `default` | |
| `container` | string | No | auto | Container name (for multi-container pods) |
| `tail_lines` | integer | No | `100` | Lines to return (max 5000) |
| `previous` | boolean | No | `false` | Get logs from crashed previous instance |

```bash
# Get last 200 lines from a pod
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "k8s_get_logs",
    "inputs": {
      "pod_name": "worker-6c8b5d7f9-mq4rs",
      "namespace": "production",
      "tail_lines": 200
    }
  }'
```

```bash
# Get logs from a crashed container (previous instance)
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "k8s_get_logs",
    "inputs": {
      "pod_name": "worker-6c8b5d7f9-mq4rs",
      "namespace": "production",
      "previous": true,
      "tail_lines": 50
    }
  }'
```

```json
{
  "status": "success",
  "data": {
    "pod": "worker-6c8b5d7f9-mq4rs",
    "namespace": "production",
    "container": "auto",
    "tail_lines": 50,
    "previous": true,
    "lines": 50,
    "log": "2024-04-12T10:23:41Z ERROR failed to connect to database: connection refused\n2024-04-12T10:23:41Z FATAL exiting..."
  }
}
```

---

#### `k8s_get_events`

Lists namespace events, **warnings first**. Use this when pods are not starting — it will show OOMKill, ImagePullBackOff, probe failures, and scheduling issues.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `namespace` | string | No | `default` | |
| `field_selector` | string | No | — | e.g. `"involvedObject.name=my-pod"` or `"type=Warning"` |

```bash
# All events in production namespace (warnings first)
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "k8s_get_events", "inputs": {"namespace": "production"}}'
```

```bash
# Events for a specific pod only
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "k8s_get_events",
    "inputs": {
      "namespace": "production",
      "field_selector": "involvedObject.name=worker-6c8b5d7f9-mq4rs"
    }
  }'
```

```json
{
  "status": "success",
  "data": [
    {
      "type": "Warning",
      "reason": "OOMKilled",
      "message": "Container worker was OOM killed",
      "object": "Pod/worker-6c8b5d7f9-mq4rs",
      "count": 7,
      "first_time": "2024-04-12 09:10:00+00:00",
      "last_time": "2024-04-12 10:23:41+00:00"
    }
  ]
}
```

---

#### `k8s_deploy`

Creates or updates a Kubernetes Deployment. If one exists with the same name, it is patched (rolling update).

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | string | Yes | — | Deployment name |
| `image` | string | Yes | — | Container image with tag |
| `namespace` | string | No | `default` | |
| `replicas` | integer | No | `1` | Pod replica count (1–50) |
| `port` | integer | No | `80` | Container port |

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "k8s_deploy",
    "inputs": {
      "name": "api-server",
      "image": "myregistry/api-server:v2.4.1",
      "namespace": "production",
      "replicas": 3,
      "port": 8080
    }
  }'
```

```json
{
  "status": "success",
  "data": {
    "name": "api-server",
    "namespace": "production",
    "replicas": 3,
    "image": "myregistry/api-server:v2.4.1",
    "action": "updated"
  }
}
```

---

#### `k8s_get_deployments`

Lists all deployments in a namespace with replica health and current image.

| Parameter | Type | Required | Default |
| --- | --- | --- | --- |
| `namespace` | string | No | `default` |

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "k8s_get_deployments", "inputs": {"namespace": "production"}}'
```

```json
{
  "status": "success",
  "data": [
    {
      "name": "api-server",
      "namespace": "production",
      "replicas": 3,
      "available": 3,
      "ready": 3,
      "image": "myregistry/api-server:v2.4.1",
      "conditions": [
        { "type": "Available", "status": "True", "reason": "MinimumReplicasAvailable" }
      ]
    }
  ]
}
```

---

#### `k8s_scale`

Changes the replica count of a Deployment. Supports scale-to-zero.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `name` | string | Yes | — | Deployment name |
| `replicas` | integer | Yes | — | Desired replicas (0–100) |
| `namespace` | string | No | `default` | |

```bash
# Scale up for peak traffic
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "k8s_scale", "inputs": {"name": "api-server", "replicas": 10, "namespace": "production"}}'

# Scale to zero for cost saving (e.g. staging at night)
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "k8s_scale", "inputs": {"name": "api-server", "replicas": 0, "namespace": "staging"}}'
```

```json
{
  "status": "success",
  "data": {
    "name": "api-server",
    "namespace": "production",
    "previous_replicas": 3,
    "new_replicas": 10
  }
}
```

---

#### `k8s_rollout_restart`

Triggers a rolling restart with zero downtime. Equivalent to `kubectl rollout restart`. Use this after updating a ConfigMap, Secret, or environment variable.

| Parameter | Type | Required | Default |
| --- | --- | --- | --- |
| `name` | string | Yes | — |
| `namespace` | string | No | `default` |

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "k8s_rollout_restart", "inputs": {"name": "api-server", "namespace": "production"}}'
```

```json
{
  "status": "success",
  "data": {
    "name": "api-server",
    "namespace": "production",
    "action": "rollout_restart",
    "triggered_at": "2024-04-12T10:30:00Z",
    "message": "Rolling restart triggered for deployment 'api-server'."
  }
}
```

---

#### `k8s_rollout_status`

Checks if a rollout completed. An AI agent should call this after `k8s_deploy` or `k8s_rollout_restart` to verify success before marking a task complete.

| Parameter | Type | Required | Default |
| --- | --- | --- | --- |
| `name` | string | Yes | — |
| `namespace` | string | No | `default` |

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "k8s_rollout_status", "inputs": {"name": "api-server", "namespace": "production"}}'
```

```json
{
  "status": "success",
  "data": {
    "name": "api-server",
    "namespace": "production",
    "desired": 3,
    "updated": 3,
    "ready": 3,
    "available": 3,
    "complete": true,
    "conditions": [
      { "type": "Available", "status": "True", "message": "Deployment has minimum availability." },
      { "type": "Progressing", "status": "True", "message": "ReplicaSet has successfully progressed." }
    ]
  }
}
```

---

#### `k8s_get_services`

Lists all services in a namespace with their type, ports, and external IPs.

| Parameter | Type | Required | Default |
| --- | --- | --- | --- |
| `namespace` | string | No | `default` |

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "k8s_get_services", "inputs": {"namespace": "production"}}'
```

```json
{
  "status": "success",
  "data": [
    {
      "name": "api-server",
      "namespace": "production",
      "type": "LoadBalancer",
      "cluster_ip": "10.100.0.15",
      "external_ip": "54.210.23.45",
      "ports": [
        { "port": 80, "target_port": "8080", "protocol": "TCP", "node_port": 32100 }
      ],
      "selector": { "app": "api-server" }
    }
  ]
}
```

---

#### `k8s_get_nodes`

Returns health and capacity information for every node in the cluster.

No inputs required.

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "k8s_get_nodes", "inputs": {}}'
```

```json
{
  "status": "success",
  "data": [
    {
      "name": "ip-10-0-1-42.ec2.internal",
      "ready": true,
      "roles": ["worker"],
      "k8s_version": "v1.29.2",
      "os": "Amazon Linux 2",
      "container_runtime": "containerd://1.7.2",
      "cpu": "4",
      "memory": "8192000Ki",
      "conditions": [
        { "type": "Ready", "status": "True" },
        { "type": "MemoryPressure", "status": "False" },
        { "type": "DiskPressure", "status": "False" }
      ]
    }
  ]
}
```

---

#### `k8s_delete_pod`

Deletes a specific pod. Kubernetes immediately recreates it if it belongs to a Deployment or ReplicaSet. Use this for a targeted single-pod restart instead of a full rolling restart.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `pod_name` | string | Yes | — | Exact pod name |
| `namespace` | string | No | `default` | |
| `grace_period_seconds` | integer | No | `30` | `0` for immediate kill |

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "k8s_delete_pod",
    "inputs": {
      "pod_name": "worker-6c8b5d7f9-mq4rs",
      "namespace": "production",
      "grace_period_seconds": 0
    }
  }'
```

```json
{
  "status": "success",
  "data": {
    "pod": "worker-6c8b5d7f9-mq4rs",
    "namespace": "production",
    "action": "deleted",
    "grace_period_seconds": 0,
    "message": "Pod 'worker-6c8b5d7f9-mq4rs' deleted. Kubernetes will reschedule it if managed by a controller."
  }
}
```

---

## Example Workflows

### Workflow 1: Deploy and Verify

An AI agent deploying a new version and confirming success:

```python
import requests

BASE = "http://localhost:8000"

def call(tool, inputs):
    r = requests.post(f"{BASE}/tools/execute", json={"tool_name": tool, "inputs": inputs})
    return r.json()

# 1. Deploy new version
result = call("k8s_deploy", {
    "name": "api-server",
    "image": "myregistry/api-server:v2.4.1",
    "namespace": "production",
    "replicas": 3
})

# 2. Poll rollout status
import time
for _ in range(12):   # up to 2 minutes
    status = call("k8s_rollout_status", {"name": "api-server", "namespace": "production"})
    if status["data"]["complete"]:
        print("Rollout complete!")
        break
    time.sleep(10)
else:
    # 3. Something wrong — check events
    events = call("k8s_get_events", {
        "namespace": "production",
        "field_selector": "involvedObject.name=api-server"
    })
    print("Events:", events["data"])
```

---

### Workflow 2: Debug a CrashLoopBackOff

```bash
# Step 1 — find the bad pod
curl -s -X POST http://localhost:8000/tools/execute \
  -d '{"tool_name": "k8s_get_pods", "inputs": {"namespace": "production"}}' \
  -H "Content-Type: application/json" | jq '.data[] | select(.status != "Running")'

# Step 2 — check events for root cause
curl -s -X POST http://localhost:8000/tools/execute \
  -d '{"tool_name": "k8s_get_events", "inputs": {"namespace": "production", "field_selector": "type=Warning"}}' \
  -H "Content-Type: application/json"

# Step 3 — get logs from the crashed container
curl -s -X POST http://localhost:8000/tools/execute \
  -d '{"tool_name": "k8s_get_logs", "inputs": {"pod_name": "worker-6c8b5d7f9-mq4rs", "namespace": "production", "previous": true, "tail_lines": 100}}' \
  -H "Content-Type: application/json"

# Step 4 — force restart the pod after fix
curl -s -X POST http://localhost:8000/tools/execute \
  -d '{"tool_name": "k8s_delete_pod", "inputs": {"pod_name": "worker-6c8b5d7f9-mq4rs", "namespace": "production"}}' \
  -H "Content-Type: application/json"
```

---

### Workflow 3: Provision Infrastructure with Terraform

```bash
# 1. Plan first — see what will change
curl -s -X POST http://localhost:8000/tools/execute \
  -d '{"tool_name": "terraform_plan", "inputs": {"path": "/tmp/terraform/vpc"}}' \
  -H "Content-Type: application/json"

# 2. Apply if plan looks good
curl -s -X POST http://localhost:8000/tools/execute \
  -d '{"tool_name": "terraform_apply", "inputs": {"path": "/tmp/terraform/vpc", "auto_approve": true}}' \
  -H "Content-Type: application/json"

# 3. Open a PR to track the change
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "github_create_pull_request",
    "inputs": {
      "repo": "myorg/infra",
      "title": "infra: provision new VPC for prod-eu",
      "body": "Applied via DevOps MCP Server.\n\nTerraform plan: 5 to add, 0 to change.",
      "head": "infra/vpc-prod-eu",
      "base": "main"
    }
  }'
```

---

## Adding a New Tool

No changes to core logic are needed. Three steps:

**Step 1** — Create `tools/<category>/<tool_name>.py`:

```python
# tools/monitoring/get_alerts.py

TOOL_NAME = "monitoring_get_alerts"
TOOL_DESCRIPTION = "Fetches active alerts from Prometheus AlertManager."
TOOL_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "severity": {"type": "string", "enum": ["critical", "warning", "info"]},
    },
    "additionalProperties": False,
}

def handler(severity: str = None) -> list:
    # your implementation here
    return [{"alert": "HighCPU", "severity": "warning"}]
```

**Step 2** — Register it in `server/registry.py` inside `build_registry()`:

```python
from tools.monitoring import get_alerts

registry.register(ToolEntry(
    name=get_alerts.TOOL_NAME,
    description=get_alerts.TOOL_DESCRIPTION,
    input_schema=get_alerts.TOOL_INPUT_SCHEMA,
    handler=get_alerts.handler,
    tags=["monitoring"],
))
```

**Step 3** — Done. The tool is immediately available at `/tools/execute`.

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Single file
pytest tests/test_executor.py -v

# With coverage report
pytest tests/ -v --cov=. --cov-report=term-missing

# Only tests matching a keyword
pytest tests/ -k "registry" -v
```

---

## Security Model

| Concern | Mitigation |
| --- | --- |
| Path traversal in Terraform | All paths validated against `TERRAFORM_ALLOWED_BASE_DIR` at runtime |
| Arbitrary shell execution | `subprocess.run()` with a list (never `shell=True`) |
| Dangerous EC2 types | Instance type validated against explicit allowlist before any API call |
| Accidental `terraform destroy` | Requires `confirm_destroy="DESTROY"` string + `auto_approve` |
| Global safety switch | `DRY_RUN=true` disables all destructive ops (apply, destroy, create instance) |
| Public S3 buckets | All buckets created with `BlockPublicAcls=True` by default |
| Container privilege | Docker image runs as non-root `mcpuser` |
| Credential exposure | Credentials only loaded from env vars, never logged |

---

## Troubleshooting

**`Tool 'xxx' is not registered`**
→ Check `GET /tools` to see all available tool names. Names are case-sensitive.

**`Input validation failed`**
→ The inputs don't match the tool's JSON schema. Fetch `GET /tools/{tool_name}` to see `input_schema` and required fields.

**`GITHUB_TOKEN environment variable is not set`**
→ Export the variable: `export GITHUB_TOKEN=ghp_xxx` or add it to `.env`.

**`Path '/some/path' is outside the allowed Terraform base directory`**
→ Either move your Terraform files under `TERRAFORM_ALLOWED_BASE_DIR` or update that variable.

**`Instance type 'x2.large' is not allowed`**
→ Only the types in the allowlist are permitted. Edit `ALLOWED_INSTANCE_TYPES` in `integrations/aws_client.py` to add more.

**`Server is running in DRY_RUN mode`**
→ Set `DRY_RUN=false` in your `.env` or environment to enable destructive operations.

**`Failed to load Kubernetes config`**
→ Set `KUBECONFIG` to your kubeconfig path, or run inside a pod (in-cluster config will be auto-detected).

---

## Registered Tools Summary

| # | Tool Name | Category | Description |
| --- | --- | --- | --- |
| 1 | `terraform_plan` | Terraform | Run plan, detect changes |
| 2 | `terraform_apply` | Terraform | Apply infrastructure |
| 3 | `terraform_destroy` | Terraform | Destroy (confirmation required) |
| 4 | `github_create_pull_request` | GitHub | Open a PR |
| 5 | `github_get_repo` | GitHub | Fetch repo metadata |
| 6 | `aws_create_ec2_instance` | AWS | Launch EC2 instance |
| 7 | `aws_list_ec2_instances` | AWS | List instances by state |
| 8 | `aws_create_s3_bucket` | AWS | Create bucket (public access blocked) |
| 9 | `aws_list_s3_buckets` | AWS | List all buckets |
| 10 | `k8s_deploy` | Kubernetes | Create/update Deployment |
| 11 | `k8s_get_pods` | Kubernetes | List pods with status |
| 12 | `k8s_get_logs` | Kubernetes | Tail pod logs (supports previous) |
| 13 | `k8s_get_events` | Kubernetes | Events — warnings first |
| 14 | `k8s_scale` | Kubernetes | Change replica count |
| 15 | `k8s_rollout_restart` | Kubernetes | Zero-downtime rolling restart |
| 16 | `k8s_rollout_status` | Kubernetes | Verify rollout completed |
| 17 | `k8s_get_deployments` | Kubernetes | Fleet view with image + conditions |
| 18 | `k8s_get_services` | Kubernetes | Services with ports + external IPs |
| 19 | `k8s_get_nodes` | Kubernetes | Node health + capacity |
| 20 | `k8s_delete_pod` | Kubernetes | Targeted pod restart |

---

## License

MIT — free to use, modify, and distribute.
