# DevOps MCP Server

A **production-grade Model Context Protocol (MCP) server** that exposes DevOps automation tools — Terraform, GitHub, AWS, and Kubernetes — as structured JSON endpoints consumable by AI agents (LangGraph, AutoGen, custom agents).

---

## Architecture Overview

```
devops_mcp/
├── server/          # FastAPI app, tool registry, Pydantic schemas
├── tools/           # MCP tool definitions (metadata + handler per tool)
│   ├── terraform/
│   ├── github/
│   ├── aws/
│   └── kubernetes/
├── core/            # Config, logging, auth, execution engine
├── integrations/    # Low-level SDK wrappers (boto3, PyGithub, k8s client)
└── tests/           # pytest test suite
```

**Data flow:**

```
AI Agent → POST /tools/execute
           → ToolExecutor (validates JSON schema)
           → ToolRegistry (resolves handler)
           → Tool handler (calls integration)
           → Integration (boto3 / PyGithub / subprocess / k8s SDK)
           → Structured ToolResponse ← AI Agent
```

---

## Prerequisites

| Requirement | Minimum version |
|---|---|
| Python | 3.11 |
| Terraform CLI | 1.5+ |
| Docker | 24+ (optional) |
| AWS credentials | IAM user or role |
| GitHub PAT | `repo` + `workflow` scopes |

---

## Setup

### 1. Clone & create virtual environment

```bash
git clone https://github.com/YOUR_USERNAME/devops-mcp-server.git
cd devops_mcp

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your real credentials
```

| Variable | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | GitHub tools | Personal Access Token |
| `AWS_ACCESS_KEY_ID` | AWS tools | IAM access key |
| `AWS_SECRET_ACCESS_KEY` | AWS tools | IAM secret key |
| `AWS_REGION` | AWS tools | Default region (e.g. `us-east-1`) |
| `KUBECONFIG` | K8s tools | Path to kubeconfig file |
| `TERRAFORM_ALLOWED_BASE_DIR` | Terraform tools | Root dir for all Terraform paths |
| `DRY_RUN` | Safety | `true` disables destructive ops |

### 3. Run the server

```bash
# Development
python -m server.main

# Production
uvicorn server.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The interactive API docs are available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Docker

```bash
# Build
docker build -t devops-mcp-server:latest .

# Run
docker run -p 8000:8000 \
  -e GITHUB_TOKEN=ghp_xxx \
  -e AWS_ACCESS_KEY_ID=AKIA... \
  -e AWS_SECRET_ACCESS_KEY=... \
  -e AWS_REGION=us-east-1 \
  -e DRY_RUN=false \
  devops-mcp-server:latest
```

---

## API Reference

### `GET /health`

Liveness probe.

```json
{"status": "ok", "version": "1.0.0", "tools_registered": 11}
```

---

### `GET /tools`

List all registered MCP tools.

```json
{
  "count": 11,
  "tools": [
    {
      "name": "terraform_plan",
      "description": "Runs terraform plan in the specified directory...",
      "input_schema": { "type": "object", "properties": { "path": {"type": "string"} }, "required": ["path"] }
    }
  ]
}
```

---

### `POST /tools/execute`

Execute any registered tool.

**Request body:**

```json
{
  "tool_name": "<tool_name>",
  "inputs": { ... }
}
```

**Response envelope (always):**

```json
{
  "status": "success" | "error",
  "data": { ... },
  "error": null | "error message"
}
```

---

## Example Tool Calls

### Terraform Plan

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "terraform_plan",
    "inputs": {
      "path": "/tmp/terraform/my-infra",
      "dry_run": false
    }
  }' | jq
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "stdout": "Plan: 2 to add, 0 to change, 0 to destroy.",
    "stderr": "",
    "exit_code": 2,
    "has_changes": true,
    "dry_run": false
  },
  "error": null
}
```

---

### Terraform Apply

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "terraform_apply",
    "inputs": {
      "path": "/tmp/terraform/my-infra",
      "auto_approve": true
    }
  }' | jq
```

---

### Create GitHub Pull Request

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "github_create_pull_request",
    "inputs": {
      "repo": "myorg/myrepo",
      "title": "feat: add new feature",
      "body": "## Summary\n- Added XYZ\n\n## Test Plan\n- [ ] Unit tests pass",
      "head": "feature/my-branch",
      "base": "main"
    }
  }' | jq
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "number": 42,
    "url": "https://github.com/myorg/myrepo/pull/42",
    "state": "open",
    "title": "feat: add new feature",
    "head": "feature/my-branch",
    "base": "main"
  },
  "error": null
}
```

---

### Launch EC2 Instance

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "aws_create_ec2_instance",
    "inputs": {
      "name": "web-server-01",
      "instance_type": "t3.micro",
      "ami_id": "ami-0c55b159cbfafe1f0",
      "dry_run": true
    }
  }' | jq
```

---

### Deploy to Kubernetes

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "k8s_deploy",
    "inputs": {
      "name": "my-app",
      "image": "nginx:1.25",
      "namespace": "production",
      "replicas": 3,
      "port": 80
    }
  }' | jq
```

---

### List Pods

```bash
curl -s -X POST http://localhost:8000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "k8s_get_pods",
    "inputs": { "namespace": "production" }
  }' | jq
```

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## Adding a New Tool

1. Create `tools/<category>/<tool_name>.py` with:
   - `TOOL_NAME`, `TOOL_DESCRIPTION`, `TOOL_INPUT_SCHEMA` constants
   - `handler(**kwargs)` function

2. Register it in `server/registry.py` inside `build_registry()`:

```python
from tools.mycat import mytool

registry.register(ToolEntry(
    name=mytool.TOOL_NAME,
    description=mytool.TOOL_DESCRIPTION,
    input_schema=mytool.TOOL_INPUT_SCHEMA,
    handler=mytool.handler,
    tags=["mycat"],
))
```

**That's it.** No changes to the core executor, server, or schemas are needed.

---

## Security

- Terraform paths are validated against `TERRAFORM_ALLOWED_BASE_DIR` — no path traversal possible.
- `shell=True` is never used in subprocess calls.
- EC2 instance types are validated against an explicit allowlist.
- Terraform destroy requires `confirm_destroy="DESTROY"` in addition to `auto_approve`.
- `DRY_RUN=true` globally disables all destructive operations.
- The Docker image runs as a non-root user (`mcpuser`).
- S3 buckets are created with all public access blocked by default.

---

## Registered Tools

| Tool Name | Category | Description |
|---|---|---|
| `terraform_plan` | Terraform | Run plan, capture output |
| `terraform_apply` | Terraform | Apply infrastructure changes |
| `terraform_destroy` | Terraform | Destroy infrastructure (requires confirmation) |
| `github_create_pull_request` | GitHub | Open a PR |
| `github_get_repo` | GitHub | Fetch repo metadata |
| `aws_create_ec2_instance` | AWS | Launch EC2 instance |
| `aws_list_ec2_instances` | AWS | List EC2 instances |
| `aws_create_s3_bucket` | AWS | Create S3 bucket |
| `aws_list_s3_buckets` | AWS | List S3 buckets |
| `k8s_deploy` | Kubernetes | Create/update Deployment |
| `k8s_get_pods` | Kubernetes | List pods in namespace |

---

## License

MIT
