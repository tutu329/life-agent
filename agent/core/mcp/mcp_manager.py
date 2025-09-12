from typing import List, Optional, Dict, Any, Iterable, Callable
from pydantic import BaseModel, Field, ConfigDict
import asyncio
from pprint import pprint

from agent.core.response_api.response_api_tool_agent import Tool_Property, Tool_Parameters, Tool_Request

# -------------------------------
# 内部：真正的异步实现（保持原有逻辑）
# -------------------------------
async def _list_server_and_tools_async(server_url: str):
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    async with sse_client(url=server_url) as streams, ClientSession(*streams) as session:
        initialize_response = await session.initialize()
        list_tools_response = await session.list_tools()
        return initialize_response, list_tools_response

async def _get_mcp_tools_async(server_url: str, allowed_tools: Optional[Iterable[str]] = None) -> List[Tool_Request]:
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    allowed: Optional[set] = set(allowed_tools) if allowed_tools else None

    def _pick_json_type(t: Any) -> str:
        """规范化 JSON Schema 的 type 到 {'integer','number','boolean','string'} 四选一。"""
        allowed_types = {"integer", "number", "boolean", "string"}
        if isinstance(t, list):
            for cand in t:
                if cand in allowed_types:
                    return cand
            return "string"
        if not t:
            return "string"
        return t if t in allowed_types else "string"

    async with sse_client(url=server_url) as streams, ClientSession(*streams) as session:
        await session.initialize()
        list_tools_response = await session.list_tools()

        tool_requests: List[Tool_Request] = []
        for tool in list_tools_response.tools:
            name: str = getattr(tool, "name", "") or ""
            if allowed is not None and name not in allowed:
                continue

            description: str = getattr(tool, "description", "") or ""
            input_schema: Dict[str, Any] = getattr(tool, "inputSchema", {}) or {}

            schema_props: Dict[str, Any] = input_schema.get("properties", {}) or {}
            schema_required: List[str] = input_schema.get("required", []) or []

            props: Dict[str, Tool_Property] = {}
            for prop_name, prop_def in schema_props.items():
                p_type = _pick_json_type(prop_def.get("type"))
                p_desc = prop_def.get("description") or ""
                p_enum = prop_def.get("enum")
                if p_enum is not None and not isinstance(p_enum, list):
                    p_enum = None
                props[prop_name] = Tool_Property(
                    type=p_type,
                    description=p_desc,
                    enum=p_enum,
                )

            parameters = Tool_Parameters(
                type="object",
                properties=props,
                required=list(schema_required),
                additionalProperties=False,
            )

            tr = Tool_Request(
                type="function",
                name=name,
                description=description,
                strict=True,
                parameters=parameters,
                func=None,
            )
            tool_requests.append(tr)

        return tool_requests

# -------------------------------
# 对外：同步封装（阻塞调用）
# -------------------------------
def list_server_and_tools(server_url: str):
    """
    同步版本：返回 (initialize_response, list_tools_response)
    """
    return asyncio.run(_list_server_and_tools_async(server_url))

def get_mcp_server_tool_names(server_url: str):
    initialize_response, list_tools_response = list_server_and_tools(server_url)
    tool_names = [tool.name for tool in list_tools_response.tools]
    print('tools: ', tool_names)
    return tool_names

def get_mcp_server_tools(server_url: str, allowed_tools: Optional[Iterable[str]] = None) -> List[Tool_Request]:
    """
    同步版本：返回 List[Tool_Request]
    """
    return asyncio.run(_get_mcp_tools_async(server_url, allowed_tools))

# -------------------------------
# 同步 main()
# -------------------------------
def main():
    server_url = "https://powerai.cc:8011/mcp/sqlite/sse"
    get_mcp_server_tool_names(server_url)

    allowed = ["read_query", "write_query"]
    tools = get_mcp_server_tools(
        server_url,
        # allowed_tools = allowed     # 不传则不过滤
    )

    for t in tools:
        pprint(t)

if __name__ == "__main__":
    main()