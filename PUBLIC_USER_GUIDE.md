# Public User Guide

This guide is for end users who want to run and use the DevOps MCP Server safely.

## 1. What This Server Provides

After setup, your AI client can call tools for:
- Kubernetes (`pods`, `logs`, `events`, `deployments`, `services`, `ingresses`)
- Terraform (`plan`, `state list`, `show`, `output`, guarded `apply`)
- AWS (`cost`, `EC2`, `S3`, `ECS`)
- GitHub Actions (`pipeline runs`, `failed jobs`)

## 2. Prerequisites

- Python `3.11+`
- Terraform CLI installed and available in `PATH`
- Kubernetes access (`~/.kube/config`) for local mode
- AWS credentials configured for `boto3`
- Optional: `GITHUB_TOKEN` for private repos / higher GitHub API limits

## 3. Local Setup (stdio)

```bash
git clone https://github.com/MaripeddiSupraj/devops-mcp-server.git
cd devops-mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run local verification:

```bash
make verify
```

Start server:

```bash
python app/server.py
```

Default transport is `stdio`, which is what Cursor/Windsurf/VSCode MCP clients typically use.

## 4. Recommended Local Environment Variables

```bash
export TERRAFORM_ALLOW_UNRESTRICTED=false
export TERRAFORM_ALLOWED_ROOTS="/absolute/path/to/infra"
export TERRAFORM_APPLY_REQUIRE_APPROVAL=true
export TERRAFORM_APPLY_APPROVAL_SECRET="replace-with-long-random-secret"
export TERRAFORM_APPLY_TOKEN_TTL_SECONDS=300
```

Optional auth values for SSE/HTTP mode:

```bash
export MCP_AUTH_ENABLED=true
export MCP_AUTH_TOKENS="token-1,token-2"
export MCP_AUTH_ISSUER_URL="https://your-domain.example"
export MCP_AUTH_RESOURCE_SERVER_URL="https://your-domain.example"
```

## 5. Kubernetes Deployment (SSE)

The project includes a ready manifest in [deployment.yaml](/Users/maripeddisupraj/Documents/Codex_Work/devops-mcp-server/deployment.yaml) with:
- dedicated `ServiceAccount`
- readonly `ClusterRole` and `ClusterRoleBinding`
- secret-based env injection for auth + apply approval secret
- safer container security context

Deploy:

```bash
kubectl apply -f deployment.yaml
```

## 6. Terraform Apply Approval Token (Required by Default)

`run_terraform_apply` requires all of:
- `approval_reason`
- `approval_requested_at_epoch`
- `approval_token`
- optional `correlation_id`

The token is validated as HMAC-SHA256 with:
- secret: `TERRAFORM_APPLY_APPROVAL_SECRET`
- payload: `"{directory}|{approval_requested_at_epoch}|{approval_reason}"`
- TTL: `TERRAFORM_APPLY_TOKEN_TTL_SECONDS`

If token is invalid or expired, apply is rejected and logged as an `AUDIT` event.

## 7. Example Tool Usage

- `get_kubernetes_pods(namespace="staging")`
- `get_kubernetes_logs(namespace="staging", pod_name="api-123")`
- `run_terraform_plan(directory="/workspace/infra/staging")`
- `estimate_cost(service="all")`
- `get_pipeline_status(owner="ORG", repo="REPO")`

## 8. Public Deployment Safety Checklist

- Keep `TERRAFORM_APPLY_REQUIRE_APPROVAL=true`
- Use strong secrets for `MCP_AUTH_TOKENS` and `TERRAFORM_APPLY_APPROVAL_SECRET`
- Never commit secrets to Git
- Use least-privilege IAM and Kubernetes RBAC
- Restrict network access to SSE endpoint (internal only when possible)
- Keep image and dependencies updated

## 9. Troubleshooting

- `No module named mcp`:
  - activate virtualenv and reinstall deps
- Kubernetes auth/plugin warnings:
  - verify kube auth plugin is installed and can read its config path
- `Invalid terraform directory`:
  - ensure target directory exists and is under `TERRAFORM_ALLOWED_ROOTS`
- `approval_token is invalid or expired`:
  - regenerate token with matching directory/reason/timestamp and valid TTL

## 10. More Docs

- [README.md](/Users/maripeddisupraj/Documents/Codex_Work/devops-mcp-server/README.md)
- [USAGE_GUIDE.md](/Users/maripeddisupraj/Documents/Codex_Work/devops-mcp-server/USAGE_GUIDE.md)
- [AI_DEVELOPER_GUIDE.md](/Users/maripeddisupraj/Documents/Codex_Work/devops-mcp-server/AI_DEVELOPER_GUIDE.md)
- [SECURITY.md](/Users/maripeddisupraj/Documents/Codex_Work/devops-mcp-server/SECURITY.md)
- [CONTRIBUTING.md](/Users/maripeddisupraj/Documents/Codex_Work/devops-mcp-server/CONTRIBUTING.md)
