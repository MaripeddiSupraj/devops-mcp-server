# DevOps MCP Server: User Guide

Welcome! This guide is written for engineers and developers who want to empower their AI Assistants (like Cursor, Windsurf, Claude Code, or LangGraph) to act as autonomous DevOps engineers.

By connecting this server to your AI, you give it the ability to read Kubernetes clusters, inspect Terraform state, and discover AWS infrastructure directly from your chat prompt.

---

## What is this?
The **Model Context Protocol (MCP)** is a standardized way for AI agents to call external tools. This repository is an MCP Server built using Python and `FastMCP`. It wraps complex CLI commands (like `kubectl` and `terraform`) into clean JSON APIs that the AI can understand.

---

## 🛠️ Step 1: Prerequisites
Since this server executes real infrastructure commands on your behalf, the host machine running the server needs the correct software and credentials.

1. **Python**: `3.11` or higher. (Or just use `uv`!)
2. **Terraform**: The `terraform` CLI binary must be installed and in your system's PATH.
3. **AWS Credentials**: The server uses standard `boto3`. You must be authenticated locally (e.g., via `aws sso login` or having the `AWS_ACCESS_KEY_ID` environment variables set).
4. **Kubernetes Credentials**: You must have a valid `~/.kube/config` file with access to your cluster.

---

## 🔌 Step 2: Installation

We recommend using [`uv`](https://docs.astral.sh/uv/) to run the server without polluting your global environment. You don't even need to clone the repository!

```bash
uvx --from git+https://github.com/MaripeddiSupraj/devops-mcp-server.git devops-mcp-server
```

Alternatively, you can install it globally via pip:
```bash
pip install git+https://github.com/MaripeddiSupraj/devops-mcp-server.git
devops-mcp-server
```

---

## 💬 Step 3: How to Speak to the AI

Now that your AI is connected, you don't need to write code. You just talk to it like a senior engineer. The AI will automatically decide which tools to call.

**Example: Debugging Kubernetes**
> *"Hey, the staging environment is down. Can you check the deployments in the `staging` namespace, look for any CrashLoopBackOffs, and fetch the logs for the failing pods?"*

**Example: Terraform Auditing**
> *"I'm working in the `infra/prod` directory. Can you show me the terraform plan? If it looks good, list all the resources currently in the state file."*

**Example: CI/CD Pipeline Checks**
> *"Did the latest set of GitHub Actions pass for the `MaripeddiSupraj/devops-mcp-server` repository? If it failed, show me exactly which test jobs failed so I can fix them."*

**Example: AWS Discovery**
> *"I need to know how many EC2 instances we have running in `us-east-1` and what our AWS cost estimate is for the last 30 days."*

---

## ⚠️ Troubleshooting

If your AI complains that a tool failed:
- **"Kubernetes client not initialized"**: The server could not find your `~/.kube/config`. Ensure it is mounted or passed correctly in your MCP settings.
- **"AWS Credentials not found"**: Ensure your `AWS_PROFILE` is set or you have run `aws sso login`. In Cursor/Claude Desktop, you may need to explicitly pass `AWS_PROFILE` in the MCP `env` config.
- **"Directory does not exist"**: When asking the AI to run Terraform, ensure you give it the correct absolute path to your Terraform directory.
