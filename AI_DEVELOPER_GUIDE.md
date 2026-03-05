# AI Developer Guide: DevOps Infrastructure MCP Server

## 1. Project Overview
This repository contains a **DevOps Infrastructure MCP (Model Context Protocol) Server**. It is designed to act as a bridge between an AI Agent (like a LangGraph autonomous agent, or IDE AI like Cursor) and core DevOps infrastructure (Kubernetes, AWS, Terraform).

When an AI Agent is connected to this server, it gains the ability to securely query production environments, run infrastructure planning commands, and analyze cloud costs—all without requiring a human to manually run the CLI commands.

---

## 2. Architecture

```text
Developer / DevOps
        │
        ▼
AI Agent (LangGraph / Claude / Cursor)
        │
        ▼
   MCP Client (JSON-RPC)
        │
        ▼
DevOps MCP Server (FastMCP)
        │
 ┌──────┼──────────┬──────────┐
 │      │          │          │
Kubernetes   Terraform    AWS Cost
 │            │            │
kubectl     terraform     boto3
```

- **Framework**: Developed using `FastMCP`, which abstracts JSON-RPC complexity and allows tool registration via Python decorators (`@mcp.tool()`).
- **Transport Modes**:
  - `stdio`: Used when running the script directly (e.g., connected as a local tool in Cursor/Windsurf).
  - `sse` (Server-Sent Events): Used when the server runs in a container/Kubernetes so agents can talk to it over HTTP.

---

## 3. Available Tools & Their Implementations

### A. Kubernetes Tool (`get_kubernetes_pods`)
- **Location**: `app/tools/kubernetes_tools.py`
- **Purpose**: Returns the real-time status of Pods in a given Kubernetes namespace.
- **How it works**:
  - Uses the official `kubernetes` Python package.
  - Dynamically detects its environment: If running inside a cluster, it uses `load_incluster_config()` (relying on the Pod's ServiceAccount). If running locally, it uses `load_kube_config()` (relying on `~/.kube/config`).
  - Iterates through the Pods and maps them into a clean JSON structure summarizing their name, status (e.g., `Running` or `CrashLoopBackOff`), and restart counts.

### B. Terraform Tool (`run_terraform_plan`)
- **Location**: `app/tools/terraform_tools.py`
- **Purpose**: Simulates changes against infrastructure by executing a Terraform plan.
- **How it works**:
  - Requires the `terraform` CLI to be installed on the host mechanism (which is why it is explicitly installed in the `Dockerfile`).
  - Accepts a `directory` path. It executes `terraform init`, followed by `terraform plan`, using the `subprocess` module (`app/utils/shell.py`).
  - Returns the raw plan output to the agent.

### C. AWS Cost Explorer Tool (`estimate_aws_cost`)
- **Location**: `app/tools/aws_cost_tools.py`
- **Purpose**: Retrieves AWS billing metrics to predict or summarize infrastructure costs.
- **How it works**:
  - Built using `boto3`. Requires the environment to have AWS credentials configured (via IAM Roles, ENV vars, or `~/.aws/credentials`).
  - **Dynamic execution**: If the AI doesn't know the exact dates to query, the tool defaults to querying the *last 30 days* of history.
  - Returns an aggregated view of unblended costs grouped by time periods.

---

## 4. Deployment Guide

### Local Development (As a local AI Tool)
If you want to attach this MCP server to a local AI IDE (like Cursor) for testing:
1. Ensure you have Python installed.
2. Activate the virtual environment (`source venv/bin/activate`).
3. Add the tool to your IDE's MCP configuration using the command:
   ```json
   {
     "mcpServers": {
       "devops-mcp": {
         "command": "/path/to/repo/venv/bin/python",
         "args": ["/path/to/repo/app/server.py"]
       }
     }
   }
   ```

### Kubernetes Deployment (Production)
The repository contains everything needed to deploy this as an internal microservice inside your cluster.

1. **Docker Build**
   The provided `Dockerfile` builds a minimal Python 3.11 environment, installs the Terraform CLI, sets the default MCP transport explicitly to `sse` (so it binds to an HTTP port), and installs the Python requirements.
   ```bash
   docker build -t devops-mcp:latest .
   ```

2. **Kubernetes Rollout**
   The `deployment.yaml` manages the ReplicaSet and a ClusterIP Service.
   ```bash
   kubectl apply -f deployment.yaml
   ```
   *CRITICAL NOTE FOR AI/DEVOPS DEPLOYING THIS*: Ensure the `serviceAccountName` specified in the Deployment (`default` right now) is bound to an AWS IAM Role via IRSA (IAM Roles for Service Accounts) and a Kubernetes RoleBinding that allows it to `list` Pods across namespaces. Otherwise, the tools will fail due to lack of authorization.

---

## 5. Next Steps for Expansion
When you are ready to expand this project, consider adding these tools:
- **`restart_kubernetes_deployment(namespace, deployment_name)`**: Using `AppsV1Api` to trigger a rolling restart.
- **`get_kubernetes_logs(namespace, pod_name)`**: Using `CoreV1Api.read_namespaced_pod_log()`.
- **`run_terraform_apply(directory)`**: (Highly sensitive, requires approval loops).
- **`get_github_actions_status(repo)`**: Integrate `PyGithub` to check CI/CD pipeline states.
