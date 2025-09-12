from typing import List, Optional, Dict, Any, Iterable, Callable
from pydantic import BaseModel, Field, ConfigDict
import asyncio
from pprint import pprint

# Define the Tool_Request and related classes
class Tool_Property(BaseModel):
    type: str  # For example "integer", "string", etc.
    description: str
    enum: Optional[List[str]] = None

class Tool_Parameters(BaseModel):
    type: str = 'object'
    properties: Dict[str, Tool_Property]
    required: List[str] = Field(default_factory=list)
    additionalProperties: bool = False

class Tool_Request(BaseModel):
    type: str = 'function'
    name: str
    description: str
    strict: bool = True
    parameters: Tool_Parameters
    func: Optional[Callable] = Field(default=None, exclude=True, repr=False)
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')

# MCP Server communication function
async def list_server_and_tools(server_url: str):
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    async with sse_client(url=server_url) as streams, ClientSession(*streams) as session:
        initialize_response = await session.initialize()
        list_tools_response = await session.list_tools()
        return initialize_response, list_tools_response

async def get_mcp_tools(server_url: str, allowed_tools: Optional[Iterable[str]] = None) -> List[Tool_Request]:
    """
    从 MCP 服务器获取工具清单，并转换为 List[Tool_Request]。
    :param server_url: 形如 "https://host:port/mcp/sqlite/sse"
    :param allowed_tools: 可迭代的工具名白名单；为 None/空则不过滤
    """
    # 延迟导入，避免模块未安装时影响其他逻辑
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    allowed: Optional[set] = set(allowed_tools) if allowed_tools else None

    def _pick_json_type(t: Any) -> str:
        """规范化 JSON Schema 的 type 字段到 {'integer','number','boolean','string'} 四选一。"""
        allowed_types = {"integer", "number", "boolean", "string"}
        # 可能是列表（如 ["string","null"]）
        if isinstance(t, list):
            for cand in t:
                if cand in allowed_types:
                    return cand
            # 列表里没有我们支持的 → 退回 string
            return "string"
        # 可能是 None / 未给出
        if not t:
            return "string"
        # 单值
        return t if t in allowed_types else "string"

    async with sse_client(url=server_url) as streams, ClientSession(*streams) as session:
        # 初始化 + 拉取工具
        await session.initialize()
        list_tools_response = await session.list_tools()

        tool_requests: List[Tool_Request] = []

        for tool in list_tools_response.tools:
            name: str = getattr(tool, "name", "") or ""
            if allowed is not None and name not in allowed:
                continue

            description: str = getattr(tool, "description", "") or ""
            input_schema: Dict[str, Any] = getattr(tool, "inputSchema", {}) or {}

            # 解析 JSON Schema
            schema_props: Dict[str, Any] = input_schema.get("properties", {}) or {}
            schema_required: List[str] = input_schema.get("required", []) or []

            # 映射到你的 Tool_Property
            props: Dict[str, Tool_Property] = {}
            for prop_name, prop_def in schema_props.items():
                p_type = _pick_json_type(prop_def.get("type"))
                p_desc = prop_def.get("description") or ""
                p_enum = prop_def.get("enum")  # 可能不存在
                # 若 enum 不是列表，做个兜底
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
                func=None,  # 不从远端携带执行体
            )
            tool_requests.append(tr)

        return tool_requests

# Main function to test the get_mcp_tools
async def main():
    server_url = "https://powerai.cc:8011/mcp/sqlite/sse"

    initialize_response, list_tools_response = await list_server_and_tools(server_url)

    print('tools: ', [tool.name for tool in list_tools_response.tools])

    allowed_tools = ["read_query", "write_query"]  # Example of allowed tools
    tools = await get_mcp_tools(
        server_url,
        # allowed_tools=allowed_tools  # 不传则不过滤
    )
    for t in tools:
        pprint(t)
        # pprint(t.model_dump())

if __name__ == "__main__":
    asyncio.run(main())
