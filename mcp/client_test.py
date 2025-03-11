# conda activate mcp

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# from config import get_members_name_list

async def main():
    # Configure the server process to launch (use Python to run server.py)
    server_params = StdioServerParameters(
        command="python",
        args=["server_test.py"]
    )

    # Launch the MCP server as a subprocess and open a stdio connection
    async with stdio_client(server_params) as (read, write):
        # Create a client session over the stdio transport
        async with ClientSession(read, write) as session:
            # Initialize the MCP session (handshake with the server)
            await session.initialize()

            # Call the "add" tool on the server with arguments
            result_raw = await session.call_tool("add", arguments={"a": 5, "b": 7})

            print(f'result_raw: {result_raw}')
            print(f'result_raw.content: {result_raw.content!r}')
            print(f'result_raw.content[0]: {result_raw.content[0]!r}')
            print(f'result_raw.content[0].type: {result_raw.content[0].type!r}')
            print(f'result_raw.content[0].text: {result_raw.content[0].text!r}')
            print(f'result_raw.content[0].annotations: {result_raw.content[0].annotations!r}')

            # print(get_members_name_list(result_raw))

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())