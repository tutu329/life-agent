import asyncio
from pprint import pprint

async def list_server_and_tools(server_url: str):
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    async with sse_client(url=server_url) as streams, ClientSession(*streams) as session:
        initialize_response = await session.initialize()
        list_tools_response = await session.list_tools()
        return initialize_response, list_tools_response

async def call_tool(server_url: str, tool_name: str, args: dict):
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    async with sse_client(url=server_url) as streams, ClientSession(*streams) as session:
        # 初始化
        await session.initialize()

        # 调用具体工具
        result = await session.call_tool(
            name=tool_name,
            arguments=args,
        )
        return result

def main():
    result = asyncio.run(list_server_and_tools("https://powerai.cc:8011/mcp/sqlite/sse"))
    print(result)
    initialize_response, list_tools_response = result
    print(list_tools_response)
    for tool in list_tools_response.tools:
        print(tool.model_dump())

    result = asyncio.run(
        call_tool(
            "https://powerai.cc:8011/mcp/sqlite/sse",
            tool_name="read_query",
            args={"query": "SELECT name FROM sqlite_master WHERE type='table';"}
        )
    )
    pprint(result.model_dump())   # Pydantic 对象转 dict

if __name__ == "__main__":
    main()
