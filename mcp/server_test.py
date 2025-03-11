# conda activate mcp

from mcp.server.fastmcp import FastMCP

# Initialize an MCP server instance
mcp = FastMCP("AddServer")  # Name of the server (arbitrary)

# Define an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers and return the result."""
    return a + b

if __name__ == "__main__":
    # Run the MCP server (listens for client connections via STDIO)
    mcp.run()
