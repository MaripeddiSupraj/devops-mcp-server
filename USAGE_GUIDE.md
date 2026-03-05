# DevOps MCP Server: User Guide

Welcome! This guide is written for engineers and developers who want to empower their AI Assistants (like Cursor, Windsurf, Claude Code, or LangGraph) to act as autonomous DevOps engineers.

By connecting this server to your AI, you give it the ability to read Kubernetes clusters, inspect Terraform state, and discover AWS infrastructure directly from your chat prompt.

---

## What is this?
The **Model Context Protocol (MCP)** is a standardized way for AI agents to call external tools. This repository is an MCP Server built using Python and `FastMCP`. It wraps complex CLI commands (like `kubectl` and `terraform`) into clean JSON APIs that the AI can understand.

---

## 🛠️ Step 1: Prerequisites
Since this server executes real infrastructure commands on your behalf, the host machine running the server needs the correct software and credentials.

1. **Python**: `3.11` or higher.
2. **Terraform**: The `terraform` CLI binary must be installed and in your system's PATH.
3. **AWS Credentials**: The server uses standard `boto3`. You must be authenticated locally (e.g., via `aws sso login` or having the `AWS_ACCESS_KEY_ID` environment variables set).
4. **Kubernetes Credentials**: You must have a valid `~/.kube/config` file with access to your cluster.

---

## 🔌 Step 2: Installation
Clone the repository and install the dependencies in a virtual environment.

```bash
git clone https://github.com/MaripeddiSupraj/devops-mcp-server.git
cd devops-mcp-server

# Create an isolated python environment
python -m venv venv
source venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

---

## 🤖 Step 3: Connecting Your AI (Cursor Example)
The easiest way to use this is locally with an AI code editor like Cursor.

1. Open Cursor's settings.
2. Navigate to **Features** -> **MCP Servers**.
3. Click **Add New MCP Server**.
4. Set the name to `DevOps`.
5. Set the type to `command`.
6. For the command, you must provide the absolute path to the virtual environment's python, and the absolute path to `server.py`. 

**Example Command (Update your paths):**
```text
/Users/YOUR_NAME/devops-mcp-server/venv/bin/python /Users/YOUR_NAME/devops-mcp-server/app/server.py
```

Click save. You should see a green light indicating the server is connected and the tools are registered!

---

## 💬 Step 4: How to Speak to the AI

Now that your AI is connected, you don't need to write code. You just talk to it like a senior engineer. The AI will automatically decide which tools to call.

**Example: Debugging Kubernetes**
> *"Hey, the staging environment is down. Can you check the deployments in the `staging` namespace, look for any CrashLoopBackOffs, and fetch the logs for the failing pods?"*

**Example: Terraform Auditing**
> *"I'm working in the `infra/prod` directory. Can you show me the terraform plan? If it looks good, list all the resources currently in the state file."*

**Example: AWS Discovery**
> *"I need to know how many EC2 instances we have running in `us-east-1` and what our AWS cost estimate is for the last 30 days."*

---

## 🚢 Advanced: Deploying for LangGraph / CI/CD
If you are building an automated LangGraph pipeline or AutoGPT agent, you don't want to run this locally. You want it deployed in your cluster.

We provide a `Dockerfile` and a `deployment.yaml`.
When deployed to Kubernetes, the server automatically switches to **SSE Transport Mode** (Server-Sent Events) and binds to HTTP port `8000`.

Your central LangGraph agent can then hit this endpoint `http://devops-mcp.default.svc.cluster.local:8000/sse` to execute infrastructure operations inside the VPC. 

*Note: Ensure the Kubernetes `ServiceAccount` attached to the deployment has the correct RBAC rules and IRSA (IAM Roles for Service Accounts) policies.*
