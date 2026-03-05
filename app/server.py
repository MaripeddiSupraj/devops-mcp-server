import os
from mcp.server.fastmcp import FastMCP

from app.tools.kubernetes_tools import (
    get_pods,
    get_kubernetes_logs as k8s_logs,
    get_kubernetes_events as k8s_events,
    get_kubernetes_deployments as k8s_deployments,
    get_kubernetes_services as k8s_services,
    get_kubernetes_ingresses as k8s_ingresses
)
from app.tools.terraform_tools import (
    terraform_plan,
    terraform_state_list as tf_state_list,
    terraform_show as tf_show,
    terraform_output as tf_output,
    terraform_apply as tf_apply
)
from app.tools.aws_tools import (
    estimate_aws_cost,
    list_aws_ec2_instances as aws_ec2,
    list_aws_s3_buckets as aws_s3,
    list_aws_ecs_clusters as aws_ecs
)
from app.utils.logger import logger

# Initialize FastMCP Server
mcp = FastMCP("DevOps MCP Server")

# ==========================================
# KUBERNETES TOOLS
# ==========================================

@mcp.tool()
def get_kubernetes_pods(namespace: str) -> list[dict]:
    """Get pods in a Kubernetes namespace."""
    logger.info(f"MCP Tool Call: get_kubernetes_pods(namespace={namespace})")
    return get_pods(namespace)

@mcp.tool()
def get_kubernetes_logs(namespace: str, pod_name: str, container_name: str = None) -> dict:
    """Get the raw logs for a specific pod in a namespace."""
    logger.info(f"MCP Tool Call: get_kubernetes_logs(namespace={namespace}, pod_name={pod_name})")
    return k8s_logs(namespace, pod_name, container_name)

@mcp.tool()
def get_kubernetes_events(namespace: str) -> list[dict]:
    """Get the most recent system events in a namespace to debug crash loops or scheduling failures."""
    logger.info(f"MCP Tool Call: get_kubernetes_events(namespace={namespace})")
    return k8s_events(namespace)

@mcp.tool()
def get_kubernetes_deployments(namespace: str) -> list[dict]:
    """Get deployments and their readiness states in a namespace."""
    logger.info(f"MCP Tool Call: get_kubernetes_deployments(namespace={namespace})")
    return k8s_deployments(namespace)

@mcp.tool()
def get_kubernetes_services(namespace: str) -> list[dict]:
    """Get services, internal cluster IPs, and NodePorts in a namespace."""
    logger.info(f"MCP Tool Call: get_kubernetes_services(namespace={namespace})")
    return k8s_services(namespace)

@mcp.tool()
def get_kubernetes_ingresses(namespace: str) -> list[dict]:
    """Get ingresses and external routing hostnames in a namespace."""
    logger.info(f"MCP Tool Call: get_kubernetes_ingresses(namespace={namespace})")
    return k8s_ingresses(namespace)

# ==========================================
# TERRAFORM TOOLS
# ==========================================

@mcp.tool()
def run_terraform_plan(directory: str) -> dict:
    """Run terraform plan in a specified directory to preview changes."""
    logger.info(f"MCP Tool Call: run_terraform_plan(directory={directory})")
    return terraform_plan(directory)

@mcp.tool()
def run_terraform_state_list(directory: str) -> dict:
    """List all tracked resources in the current Terraform state."""
    logger.info(f"MCP Tool Call: run_terraform_state_list(directory={directory})")
    return tf_state_list(directory)

@mcp.tool()
def run_terraform_show(directory: str) -> dict:
    """Show the full current active terraform state in deep JSON format."""
    logger.info(f"MCP Tool Call: run_terraform_show(directory={directory})")
    return tf_show(directory)

@mcp.tool()
def run_terraform_output(directory: str) -> dict:
    """Get all output variables (like endpoints) from the current Terraform state."""
    logger.info(f"MCP Tool Call: run_terraform_output(directory={directory})")
    return tf_output(directory)

@mcp.tool()
def run_terraform_apply(directory: str, auto_approve: bool = False) -> dict:
    """
    Run terraform apply in a specified directory.
    DANGEROUS: Do not use auto_approve=True unless explicitly authorized.
    """
    logger.info(f"MCP Tool Call: run_terraform_apply(directory={directory}, auto_approve={auto_approve})")
    return tf_apply(directory, auto_approve)

# ==========================================
# AWS TOOLS
# ==========================================

@mcp.tool()
def estimate_cost(service: str, start_date: str = None, end_date: str = None) -> dict:
    """Estimate AWS cost for a specific service. Dates (YYYY-MM-DD) default to 30 days."""
    logger.info(f"MCP Tool Call: estimate_cost(service={service})")
    return estimate_aws_cost(service, start_date, end_date)

@mcp.tool()
def list_ec2_instances(region: str) -> dict:
    """List EC2 instances, states, and IPs in a specific AWS region."""
    logger.info(f"MCP Tool Call: list_ec2_instances(region={region})")
    return aws_ec2(region)

@mcp.tool()
def list_s3_buckets() -> dict:
    """List all S3 buckets in the AWS account."""
    logger.info("MCP Tool Call: list_s3_buckets()")
    return aws_s3()

@mcp.tool()
def list_ecs_clusters(region: str) -> dict:
    """List ECS clusters and running task counts in a specific AWS region."""
    logger.info(f"MCP Tool Call: list_ecs_clusters(region={region})")
    return aws_ecs(region)


if __name__ == "__main__":
    # Check if SSE transport was requested (e.g., when running in Kubernetes)
    # Default is stdio for local use with editors like Cursor/Windsurf
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    
    logger.info(f"Starting FastMCP DevOps Server with transport: {transport}")
    
    if transport == "sse":
        # FastMCP automatically hosts an SSE server if requested
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
