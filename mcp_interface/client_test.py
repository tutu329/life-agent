# # conda activate mcp_interface
#
# import asyncio
# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client
#
# # from config import get_members_name_list
#
# async def main():
#     # Configure the server process to launch (use Python to run server.py)
#     server_params = StdioServerParameters(
#         command="python",
#         args=["server_test.py"]
#     )
#
#     # Launch the MCP server as a subprocess and open a stdio connection
#     async with stdio_client(server_params) as (read, write):
#         # Create a client session over the stdio transport
#         async with ClientSession(read, write) as session:
#             # Initialize the MCP session (handshake with the server)
#             await session.initialize()
#
#             # Call the "add" tool on the server with arguments
#             result_raw = await session.call_tool("add", arguments={"a": 5, "b": 7})
#
#             print(f'result_raw: {result_raw}')
#             print(f'result_raw.content: {result_raw.content!r}')
#             print(f'result_raw.content[0]: {result_raw.content[0]!r}')
#             print(f'result_raw.content[0].type: {result_raw.content[0].type!r}')
#             print(f'result_raw.content[0].text: {result_raw.content[0].text!r}')
#             print(f'result_raw.content[0].annotations: {result_raw.content[0].annotations!r}')
#
#             # print(get_members_name_list(result_raw))
#
# # Run the async main function
# if __name__ == "__main__":
#     asyncio.run(main())

import asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession

remote_url = "http://127.0.0.1:3000/sse"  # SSE端点地址（需替换为实际地址）

async def main():
    async with sse_client(remote_url) as (read_stream, write_stream):
        # 创建客户端会话
        async with ClientSession(read_stream, write_stream) as session:
            # 初始化MCP会话
            await session.initialize()

            print("远程MCP服务器连接成功")

            # 调用远程 add 工具
            result = await session.call_tool("add", arguments={"a": 5, "b": 7})
            print(f"远程调用 add 工具的结果为: {result}")

if __name__ == "__main__":
    asyncio.run(main())





# """MCP HTTP client example using MCP SDK."""
#
# import asyncio
# import sys
# from typing import Any
# from urllib.parse import urlparse
#
# from mcp.client.session import ClientSession
# from mcp.client.sse import sse_client
#
#
# def print_items(name: str, result: Any) -> None:
#     """Print items with formatting.
#
#     Args:
#         name: Category name (tools/resources/prompts)
#         result: Result object containing items list
#     """
#     print("", f"Available {name}:", sep="\n")
#     items = getattr(result, name)
#     if items:
#         for item in items:
#             print(" *", item)
#     else:
#         print("No items available")
#
#
# async def main(server_url: str):
#     """Connect to MCP server and list its capabilities.
#
#     Args:
#         server_url: Full URL to SSE endpoint (e.g. http://localhost:8000/sse)
#     """
#     if urlparse(server_url).scheme not in ("http", "https"):
#         print("Error: Server URL must start with http:// or https://")
#         sys.exit(1)
#
#     try:
#         async with sse_client(server_url) as streams:
#             async with ClientSession(streams[0], streams[1]) as session:
#                 await session.initialize()
#                 print("Connected to MCP server at", server_url)
#                 print_items("tools", (await session.list_tools()))
#                 print_items("resources", (await session.list_resources()))
#                 print_items("prompts", (await session.list_prompts()))
#
#     except Exception as e:
#         print(f"Error connecting to server: {e}")
#         sys.exit(1)
#
#
# if __name__ == "__main__":
#     if len(sys.argv) != 2:
#         print("Usage: uv run -- main.py <server_url>")
#         print("Example: uv run -- main.py http://localhost:8000/sse")
#         sys.exit(1)
#
#     asyncio.run(main(sys.argv[1]))
