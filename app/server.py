import os
from mcp.server.fastmcp import FastMCP

from app.tools.kubernetes_tools import get_pods
from app.tools.terraform_tools import terraform_plan
from app.tools.aws_cost_tools import estimate_aws_cost
from app.utils.logger import logger

# Initialize FastMCP Server
mcp = FastMCP("DevOps MCP Server")

@mcp.tool()
def get_kubernetes_pods(namespace: str) -> list[dict]:
    """
    Get pods in a Kubernetes namespace.
    """
    logger.info(f"MCP Tool Call: get_kubernetes_pods(namespace={namespace})")
    return get_pods(namespace)


@mcp.tool()
def run_terraform_plan(directory: str) -> dict:
    """
    Run terraform plan in a specified directory.
    """
    logger.info(f"MCP Tool Call: run_terraform_plan(directory={directory})")
    return terraform_plan(directory)


@mcp.tool()
def estimate_cost(service: str, start_date: str = None, end_date: str = None) -> dict:
    """
    Estimate AWS cost for a specific service.
    Dates are optional, defaults to the last 30 days if not provided. YYYY-MM-DD format.
    """
    logger.info(f"MCP Tool Call: estimate_aws_cost(service={service}, start={start_date}, end={end_date})")
    return estimate_aws_cost(service, start_date, end_date)


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
