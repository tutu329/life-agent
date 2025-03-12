# conda activate mcp_interface
# 注意所在文件夹'mcp_interface'不能更名为'mcp'，否则python -m mcp.server_test.py会找不到module，因为mcp文件夹和mcp库重名了
from config import get_members_name_list
from mcp.server.fastmcp import FastMCP

# Initialize an MCP server instance
mcp = FastMCP(
    name="AddServer",
    host='0.0.0.0',
    port=3000,
)  # Name of the server (arbitrary)

# Define an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers and return the result."""
    return a + b

if __name__ == "__main__":
    # Run the MCP server (listens for client connections via STDIO)
    print(f'members of mcp: {get_members_name_list(mcp)!r}')
    # members of mcp: ['add_prompt', 'add_resource', 'add_tool', 'call_tool', 'get_context',
    # 'get_prompt', 'list_prompts', 'list_resource_templates', 'list_resources', 'list_tools',
    # 'prompt', 'read_resource', 'resource', 'run', 'run_sse_async', 'run_stdio_async', 'tool']
    mcp.run()



# from fastapi import FastAPI
# from fastapi.responses import StreamingResponse
# from mcp.server.fastmcp import FastMCP
# from config import get_members_name_list
# from mcp.server.sse import SseServerTransport
#
# app = FastAPI()
#
# # 创建MCP服务器实例
# mcp = FastMCP("AddServer")
#
# # 注册工具
# @mcp.tool()
# def add(a: int, b: int) -> int:
#     """Add two numbers and return the result."""
#     return a + b
#
# # MCP SSE 端点
# @app.get("/sse")
# async def sse_endpoint():
#     transport = SseServerTransport(mcp)
#     return StreamingResponse(transport.handle(), media_type="text/event-stream")
#
# # MCP HTTP POST调用端点
# @app.post("/messages")
# async def message_endpoint(message: dict):
#     transport = SseServerTransport(mcp)
#     response = await transport.handle_request(message)
#     return response
#
# # 启动信息
# if __name__ == "__main__":
#     import uvicorn
#     print(f'members of mcp: {get_members_name_list(mcp)!r}')
#     uvicorn.run(app, host="0.0.0.0", port=3000)
