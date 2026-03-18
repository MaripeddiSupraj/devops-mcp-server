import os
from mcp.server.fastmcp import FastMCP

from app.tools.kubernetes_tools import (
    get_kubernetes_pods,
    get_kubernetes_logs,
    get_kubernetes_events,
    get_kubernetes_deployments,
    get_kubernetes_services,
    get_kubernetes_ingresses
)
from app.tools.terraform_tools import (
    run_terraform_plan,
    run_terraform_state_list,
    run_terraform_show,
    run_terraform_output,
    run_terraform_apply
)
from app.tools.aws_tools import (
    estimate_cost,
    list_ec2_instances,
    list_s3_buckets,
    list_ecs_clusters
)
from app.tools.cicd_tools import (
    get_pipeline_status,
    get_failed_pipeline_jobs
)
from app.utils.logger import logger

# Initialize FastMCP Server
mcp = FastMCP("DevOps MCP Server")

# Register CI/CD Tools
mcp.add_tool(get_pipeline_status)
mcp.add_tool(get_failed_pipeline_jobs)

# Register Kubernetes Tools
mcp.add_tool(get_kubernetes_pods)
mcp.add_tool(get_kubernetes_logs)
mcp.add_tool(get_kubernetes_events)
mcp.add_tool(get_kubernetes_deployments)
mcp.add_tool(get_kubernetes_services)
mcp.add_tool(get_kubernetes_ingresses)

# Register Terraform Tools
mcp.add_tool(run_terraform_plan)
mcp.add_tool(run_terraform_state_list)
mcp.add_tool(run_terraform_show)
mcp.add_tool(run_terraform_output)
mcp.add_tool(run_terraform_apply)

# Register AWS Tools
mcp.add_tool(estimate_cost)
mcp.add_tool(list_ec2_instances)
mcp.add_tool(list_s3_buckets)
mcp.add_tool(list_ecs_clusters)

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
