import asyncio
from mcp.server.fastmcp import FastMCP
from app.server import mcp

async def test_server():
    print("Testing MCP tools initialization...")
    print(f"Loaded Server Name: {mcp.name}")
    
    # We can fetch the tools safely
    tools = await mcp.list_tools()
    
    print("\nAvailable Tools:")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")
        
    print("\nInitialization successful.")

if __name__ == "__main__":
    asyncio.run(test_server())
