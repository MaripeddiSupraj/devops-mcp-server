# DevOps MCP Server
*The Ultimate Infrastructure Bridge for Autonomous AI Agents*

[![FastMCP Compatible](https://img.shields.io/badge/FastMCP-✅-blue)]()
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-ffd343.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()

The **DevOps MCP Server** implements the [Model Context Protocol](https://github.com/modelcontextprotocol/spec), empowering your AI Assistants (like Cursor, Claude Desktop, or Windsurf) to securely read, debug, and execute operations across your Kubernetes clusters, AWS environments, and Terraform state. 

Turn your AI into a Senior DevOps Engineer.

---

## 🔥 15 Massive Capabilities
This server equips your AI agent with deep introspection capabilities:

**Kubernetes**: Debug CrashLoopBackOffs instantly.
- List Pods, Deployments, Services, and Ingresses.
- Fetch raw container logs.
- View cluster scheduling and networking events.

**Terraform**: Understand infrastructure as code perfectly.
- Run `terraform plan` safely.
- Deep inspect state JSON (`terraform show -json`).
- Fetch generated output endpoints.
- Execute infrastructure changes (`terraform apply`).

**CI/CD (GitHub Actions)**: Troubleshoot failing builds without switching context.
- Check latest pipeline statuses.
- Extract exact failing jobs/steps from a run.

**AWS**: Discover live cloud assets.
- Enumerate EC2 instances and IPs.
- List ECS container clusters and task counts.
- Search S3 Storage buckets.
- Analyze billing metrics via Cost Explorer.

---

## 🚀 Quickstart: Local Installation

You no longer need to manually manage virtual environments! You can install the server globally or run it dynamically.

### Prerequisites
1. Python 3.11+
2. The `terraform` binary installed locally.
3. Authenticated AWS credentials (e.g. `aws sso login` or `~/.aws/credentials`).
4. Authenticated Kubernetes access (`~/.kube/config`).

### Option 1: Using `uvx` (Recommended)
If you have [`uv`](https://docs.astral.sh/uv/) installed, you can run the server directly without installing it:
```bash
uvx devops-mcp-server
```
*(Note: If installing directly from GitHub before PyPI release, use: `uvx --from git+https://github.com/MaripeddiSupraj/devops-mcp-server.git devops-mcp-server`)*

### Option 2: Using `pip`
```bash
pip install git+https://github.com/MaripeddiSupraj/devops-mcp-server.git
```
Then just start the server:
```bash
devops-mcp-server
```

---

## 🤖 IDE Configurations

### Claude Desktop Configuration
Add this to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "devops-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/MaripeddiSupraj/devops-mcp-server.git",
        "devops-mcp-server"
      ],
      "env": {
        "AWS_PROFILE": "default",
        "KUBECONFIG": "/Users/YOUR_NAME/.kube/config"
      }
    }
  }
}
```

### Cursor / Windsurf Configuration
1. Open your IDE Settings -> MCP Servers.
2. Click **Add New MCP Server**.
3. Set the type to `command`.
4. Name it `DevOps`.
5. For the command, use: `uvx --from git+https://github.com/MaripeddiSupraj/devops-mcp-server.git devops-mcp-server`
6. *(If you used pip install, the command is just `devops-mcp-server`)*

---

## 🚢 Production Deployment (For LangGraph/AutoGPT)
If you are running a centralized AI reasoning engine and want it to access your production K8s cluster or internal AWS VPC, use the Server-Sent Events (SSE) manifest.

```bash
# 1. Build the Docker Image
docker build -t devops-mcp:latest .

# 2. Deploy to Kubernetes
kubectl apply -f deployment.yaml
```

The server automatically detects it is running inside Kubernetes and will switch to:
1. `MCP_TRANSPORT=sse` (Hosts on port 8000).
2. Uses in-cluster RBAC (via the Pod's ServiceAccount) instead of looking for `~/.kube/config`.
3. Uses IAM Roles for Service Accounts (IRSA) for AWS.

---

## 🔒 Security Posture
This server executes infrastructure commands. It uses **Subprocess Command Arrays** to prevent bash injection and relies completely on the underlying IAM and RBAC rules assigned to its executing environment. 
**Never run this server with cluster-admin or AWS AdministratorAccess.**
