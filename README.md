# DevOps MCP Server
*The Ultimate Infrastructure Bridge for Autonomous AI Agents*

[![FastMCP Compatible](https://img.shields.io/badge/FastMCP-✅-blue)]()
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-ffd343.svg)]()

The **DevOps MCP Server** implements the [Model Context Protocol](https://github.com/jlowin/fastmcp), empowering your AI Assistants (like Cursor, Claude Code, or Windsurf) to securely read, debug, and execute operations across your Kubernetes clusters, AWS environments, and Terraform state. 

Turn your AI into a Senior DevOps Engineer.

---

## 🔥 15 Massive Capabilities
This server equips your AI agent with deep introspection capabilities:

**Kubernetes (`kubernetes-client`)**: Debug CrashLoopBackOffs instantly.
- List Pods, Deployments, Services, and Ingresses.
- Fetch raw container logs.
- View cluster scheduling and networking events.

**Terraform (Subprocess Router)**: Understand infrastructure as code perfectly.
- Run `terraform plan` safely.
- Deep inspect state JSON (`terraform show -json`).
- Fetch generated output endpoints.
- Execute infrastructure changes (`terraform apply`).

**CI/CD (GitHub Actions)**: Troubleshoot failing builds without switching context.
- Check latest pipeline statuses (`get_pipeline_status`).
- Extract exact failing jobs/steps from a run (`get_failed_pipeline_jobs`).

**AWS (`boto3`)**: Discover live cloud assets.
- Enumerate EC2 instances and IPs.
- List ECS container clusters and task counts.
- Search S3 Storage buckets.
- Analyze billing metrics via Cost Explorer.

---

## 🚀 Quickstart: Running Locally (For IDEs like Cursor/Windsurf)
Use this method if you want your local IDE's AI assistant to have access to your local kubeconfig, AWS credentials, and terraform states.

### Prerequisites
1. Python 3.11+
2. The `terraform` binary installed locally.
3. Authenticated AWS credentials (e.g. `aws sso login` or `~/.aws/credentials`).
4. Authenticated Kubernetes access (`~/.kube/config`).

### Setup
```bash
# Clone the repository
git clone https://github.com/YOUR_ORG/devops-mcp-server.git
cd devops-mcp-server

# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuring Cursor / Windsurf
1. Open your IDE Settings -> MCP Servers.
2. Click **Add New MCP Server**.
3. Set the type to `command`.
4. Name it `DevOps`.
5. For the command, use: `/absolute/path/to/devops-mcp-server/venv/bin/python /absolute/path/to/devops-mcp-server/app/server.py`.
6. Ensure your terminal has the necessary AWS/Kube environment variables exported. The MCP server will run in the background as a `stdio` process.

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
