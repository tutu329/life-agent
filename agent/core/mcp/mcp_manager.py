import json, os
from typing import List, Optional, Dict, Any, Iterable, Callable
from pydantic import BaseModel, Field, ConfigDict
from mcp import ClientSession
from mcp.client.sse import sse_client
import asyncio
from pprint import pprint
import config

from agent.tools.protocol import Tool_Property, Tool_Parameters, Tool_Request

DEBUG = config.Global.app_debug

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def dpprint(*args, **kwargs):
    if DEBUG:
        pprint(*args, **kwargs)

# -------------------------------
# 内部：真正的异步实现（保持原有逻辑）
# -------------------------------
async def _call_tool(server_url: str, tool_name: str, args: dict):
    async with sse_client(url=server_url) as streams, ClientSession(*streams) as session:
        # 初始化
        await session.initialize()

        # 调用具体工具
        res = await session.call_tool(
            name=tool_name,
            arguments=args,
        )
        dprint(res)
        text_list = [item.text for item in res.content]
        # result = json.dumps(res.content, ensure_ascii=False)
        dprint(text_list)
        result = '\n'.join(text_list)
        return result

async def _list_server_and_tools_async(server_url: str):
    async with sse_client(url=server_url) as streams, ClientSession(*streams) as session:
        initialize_response = await session.initialize()
        list_tools_response = await session.list_tools()
        return initialize_response, list_tools_response

# -------------------------------
# 内部：真正的异步实现（保持原有逻辑）——给每个 tool 绑定 func
# -------------------------------
async def _get_mcp_tools_async(server_url: str, allowed_tools: Optional[Iterable[str]] = None) -> List[Tool_Request]:
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

    # 绑定一个同步函数：支持 *args（按 required 顺序）+ **kwargs，最终都转成 kwargs
    def _make_bound_func(_server_url: str, _tool_name: str, _required: List[str]):
        def _caller(*args, **kwargs):
            # 把位置参数映射到 required 字段
            if args:
                # 只按 required 的顺序填充，剩余的必须通过 kwargs 传
                mapped = {k: v for k, v in zip(_required, args)}
                # 合并 kwargs（kwargs 会覆盖相同键）
                mapped.update(kwargs)
            else:
                mapped = dict(kwargs)

            # （可选）做一个最小必填校验，早点发现问题
            missing = [k for k in _required if k not in mapped]
            if missing:
                raise TypeError(f"Missing required arguments for tool '{_tool_name}': {missing}")

            # 调用你现有的同步封装
            return call_tool(_server_url, _tool_name, mapped)
        return _caller

    async with sse_client(url=server_url) as streams, ClientSession(*streams) as session:
        await session.initialize()
        list_tools_response = await session.list_tools()

        tool_requests: List[Tool_Request] = []
        tool_funcs: List[Callable] = []

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

            # 这里把 func 绑定进去
            bound_func = _make_bound_func(server_url, name, schema_required)

            tr = Tool_Request(
                type="function",
                name=name,
                description=description,
                strict=True,
                parameters=parameters,
                # func=bound_func,   # 关键：赋值给 func
            )
            tool_requests.append(tr)
            tool_funcs.append(bound_func)

        return tool_requests, tool_funcs

# -------------------------------
# 对外：同步封装（阻塞调用）
# -------------------------------
def call_tool(server_url: str, tool_name: str, args: dict):
    return asyncio.run(_call_tool(server_url, tool_name, args))

def list_server_and_tools(server_url: str):
    """
    同步版本：返回 (initialize_response, list_tools_response)
    """
    return asyncio.run(_list_server_and_tools_async(server_url))

def get_mcp_server_tool_names(server_url: str):
    initialize_response, list_tools_response = list_server_and_tools(server_url)
    tool_names = [tool.name for tool in list_tools_response.tools]
    # dprint('tools: ', tool_names)
    return tool_names

def get_mcp_server_tools(server_url: str, allowed_tools: Optional[Iterable[str]] = None):
    """
    同步版本：返回 List[Tool_Request]
    """
    return asyncio.run(_get_mcp_tools_async(server_url, allowed_tools))

# -------------------------------
# 同步 main()
# -------------------------------
def main_mcp_sqlite():
    server_url = "https://powerai.cc:8011/mcp/sqlite/sse"
    result = call_tool(
        server_url,
        tool_name="read_query",
        args={"query": "SELECT name FROM sqlite_master WHERE type='table';"}
    )
    print(result)

    get_mcp_server_tool_names(server_url)

    allowed = ["read_query", "write_query"]
    tools = get_mcp_server_tools(
        server_url,
        # allowed_tools = allowed     # 不传则不过滤
    )

    for t in tools:
        pprint(t)

def main_func_test():
    server_url = "https://powerai.cc:8011/mcp/sqlite/sse"
    tools = get_mcp_server_tools(server_url)

    # 找到 read_query 工具并直接调用其 func（既可按 required 顺序传 *args，也可 **kwargs）
    read_tool = next(t for t in tools if t.name == "read_query")
    res = read_tool.func(query="SELECT name FROM sqlite_master WHERE type='table';")
    print(res)

    # 若某工具 required = ['a','b']，也可：
    # div_res = div_tool.func(6, 3)              # 位置参数
    # div_res = div_tool.func(a=6, b=3)          # 关键字参数
    # div_res = div_tool.func(6, b=3)            # 混合（*args 覆盖 required 的前缀）

def main_mcp_tavily():
    '''
    vpn_off
    npx supergateway \
    --stdio "npx -y tavily-mcp@latest" \
    --port 8789 \
    --sse
    '''
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    # print(f'TAVILY_API_KEY: {tavily_api_key!r}')
    # server_url = f"https://mcp.tavily.com/mcp/?tavilyApiKey={tavily_api_key}"
    server_url = f"http://localhost:8789/sse"
    tools = get_mcp_server_tool_names(server_url)
    # tools = get_mcp_server_tools(server_url)
    print(tools)
    # result = call_tool(
    #     server_url,
    #     tool_name="read_query",
    #     args={"query": "SELECT name FROM sqlite_master WHERE type='table';"}
    # )
    # print(result)
    #
    # get_mcp_server_tool_names(server_url)
    #
    # allowed = ["read_query", "write_query"]
    # tools = get_mcp_server_tools(
    #     server_url,
    #     # allowed_tools = allowed     # 不传则不过滤
    # )
    #
    # for t in tools:
    #     pprint(t)

if __name__ == "__main__":
    # main_mcp_sqlite()
    # main_func_test()
    main_mcp_tavily()
