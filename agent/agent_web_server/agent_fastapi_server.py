from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
import uvicorn

import asyncio
import json
from typing import List, Dict, Any, Type, Optional

import config
from config import Port, dyellow, dred, dgreen, dcyan, dblue

# agent
from agent.core.protocol import Query_Agent_Context
from agent.tools.tool_manager import server_register_all_local_tool_on_start
from agent.core.agent_config import Agent_Config, Agent_As_Tool_Config
from agent.core.tool_agent import Tool_Agent
from agent.core.multi_agent_server import Registered_Agent_Data, server_continue_agent, server_cancel_agent, server_start_and_register_2_levels_agents_system, print_agent_status, server_get_agent_status, __server_wait_registered_agent

from contextlib import asynccontextmanager
from agent.tools.protocol import Action_Result, Tool_Call_Paras
# from agent.core.legacy_protocol import Action_Result
from dataclasses import dataclass, field, asdict

# tools
from agent.tools.folder_tool import Folder_Tool
from agent.tools.human_console_tool import Human_Console_Tool
from utils.fastapi_server import FastAPI_Endpoint_With_SSE, fastapi_show_all_routes
from agent.tools.tool_manager import Registered_Remote_Tool_Data

from config import dyellow


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ★ 启动时初始化 ★
    # 例如：一次性加载 LLM 或建立数据库池

    # 初始化agent和tool的注册
    registered_tools_dict = server_register_all_local_tool_on_start()

    # 应用开始接收请求
    yield  # <—— 应用开始接收请求

    # ★ 关闭时清理 ★
        # 如果有 close / shutdown 方法
    # 其它清理……

app = FastAPI(title="Agent FastAPI Server", lifespan=lifespan)

# 添加CORS支持，允许JavaScript调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# class Agent_Request(BaseModel):
#     query           : str
#     agent_config    : Agent_Config

class Agents_System_Request(BaseModel):
    # query               : str                                   # 如：'当前文件夹下有哪些文件'
    remote_tools        : List[Registered_Remote_Tool_Data]     # remote_tool的配置（多个）
    upper_agent_config  : Agent_Config                          # 顶层agent的配置
    lower_agents_config : List[Agent_As_Tool_Config]            # 下层agent的配置（多个）

class Agent_Status_Request(BaseModel):
    agent_id    : str

# class Query_Agent_Context(BaseModel):
#     template_filename   : str = ''
#     shared_filename     : str = ''

class Query_Agent_Request(BaseModel):
    agent_id    : str
    query       : str   # 如：'当前文件夹下有哪些文件'
    context     : Query_Agent_Context

@app.get("/")
def root():
    return {"server status": "Agent FastAPI Server 运行中..."}

@app.post("/run_agent_sync")
def run_agent_sync(request: Agents_System_Request):
    """运行Agent"""
    # 创建工具列表
    tools = [Human_Console_Tool, Folder_Tool]

    # 创建配置
    config = Agent_Config(
        base_url=request.base_url,
        api_key=request.api_key,
        llm_model_id=request.llm_model_id
    )

    agent = Tool_Agent(
        query=request.query,
        tool_classes=tools,
        agent_config=config
    )

    # 初始化和运行
    # 同步运行
    try:
        agent.init()
        success = agent.run()
        dyellow('--------------------------33---------------------------')
        dyellow(f'result: "{agent.final_answer}"')
        rtn_dict = {
            "success": success,
            "query": request.query
        }
        clean_bytes = json.dumps(rtn_dict, ensure_ascii=False).encode("utf-8", "surrogatepass")
        dyellow('--------------------------3---------------------------')
        return JSONResponse(content=json.loads(clean_bytes))
        # return rtn_dict
    except UnicodeEncodeError as e:
        return {
            "success": False,
            "query": request.query,
            "error": f"Unicode编码错误: {safe_encode(str(e))}"
        }
    except Exception as e:
        return {
            "success": False,
            "query": request.query,
            "error": safe_encode(str(e))
        }

async def event_generator(name: str):
    """
    按秒推送计数器和用户名字。
    """
    counter = 0
    while True:
        counter += 1
        message = {"name": name, "counter": counter}
        yield f"data: {json.dumps(message)}\n\n"
        await asyncio.sleep(1)

@app.post("/run_agent_stream")
async def run_agent_stream(request: Agents_System_Request):
    """
    用 POST 建立 SSE。请求体可选，示例里接收 {"name": "..."}。
    EventSource 只支持 GET，因此该端点主要供后端或 CLI 客户端消费。
    """
    try:
        body = await request.model_dump_json()
    except Exception:
        body = {}
    name = body.get("name", "anonymous")

    return StreamingResponse(
        event_generator(name),
        media_type="text/event-stream"
    )

@app.post("/api/get_agent_status")
async def get_agent_status(request:Agent_Status_Request):
    agent_status = server_get_agent_status(agent_id=request.agent_id)
    dred(f'------------------agent(id="{request.agent_id}")\'s status is "{agent_status}"-----------------')
    if agent_status:
        if agent_status.finished_one_run:
            dgreen(f'------------------agent(id="{request.agent_id}")\'s status is finished.-----------------')
        return agent_status
    else:
        return None

@app.post("/api/start_2_level_agents_system")
async def start_2_level_agents_system(request: Agents_System_Request):
    import time
    from agent.tools.tool_manager import print_all_registered_tools, server_register_all_local_tool_on_start, \
        server_register_remote_tool_dynamically, server_register_remote_tools_dynamically, Registered_Remote_Tool_Data

    # from agent.core.multi_agent_server import server_start_and_register_2_levels_agents_system, print_agent_status
    from agent.core.multi_agent_server import __server_wait_registered_agent
    from config import Port

    dblue(f'--------------------------start_2_level_agents_stream获得request参数--------------------------------')
    dblue(request)
    dblue(f'-------------------------/start_2_level_agents_stream获得request参数--------------------------------')

    # --------注册一个远程tool(需要远程开启该tool call的fastapi)--------
    # 注册local所有tool
    # server_register_all_local_tool_on_start()
    tool_ids = server_register_remote_tools_dynamically(request.remote_tools)
    print(f'start_2_level_agents_system:print_all_registered_tools()')
    print_all_registered_tools()
    # -------/注册一个远程tool(需要远程开启该tool call的fastapi)--------

    agent_data = server_start_and_register_2_levels_agents_system(
        upper_agent_config=request.upper_agent_config,
        lower_agents_config=request.lower_agents_config
    )

    # 测试用
    # __server_wait_registered_agent(agent_id=agent_data.agent_id, timeout_second=20000000)
    # server_continue_agent(agent_id=agent_data.agent_id, query='我刚才告诉你我叫什么？我刚才让你执行大的任务大的结果是什么来着？')

    time.sleep(0.5)
    print_agent_status(agent_data.agent_id)

    return agent_data.agent_id
    # return agent_data

    # __server_wait_registered_agent(agent_id, timeout_second=20000000)

    # server_continue_agent(agent_id, query='我刚才告诉你我叫什么？')
    # print_agent_status(agent_id)

@FastAPI_Endpoint_With_SSE(
    app=app,
    return_type=Registered_Agent_Data,
    return_id_name='agent_id',
    return_stream_queues_name='agent_stream_queues',
)
async def query_2_level_agents_system(request: Query_Agent_Request):
    print(f'----------------------------------request----------------------------------\n{request}')

    agent_data = server_continue_agent(agent_id=request.agent_id, query=request.query, context=request.context)
    # __server_wait_registered_agent(agent_id=request.agent_id, timeout_second=config.Agent.TIMEOUT_SECONDS)
    return agent_data

    # __server_wait_registered_agent(agent_id, timeout_second=20000000)

    # server_continue_agent(agent_id, query='我刚才告诉你我叫什么？')
    # print_agent_status(agent_id)

import platform
from pathlib import Path
import uvicorn

# … 你的其它 import、app 定义 …

if __name__ == "__main__":
    from config import get_os
    fastapi_show_all_routes(app)          # 保留原来的路由打印
    # ---------- ① 自动启用 SSL (仅限 Linux) ----------
    ssl_kwargs = {}
    if get_os() == "ubuntu":
        print(f'操作系统为：ubuntu')
        ssl_dir = Path("/home/tutu/ssl")
        certfile = ssl_dir / "powerai_public.crt"   # 公钥证书
        keyfile  = ssl_dir / "powerai.key"          # 私钥
        cafile   = ssl_dir / "powerai_chain.crt"    # CA/中间证书链

        if all(p.exists() for p in (certfile, keyfile, cafile)):
            ssl_kwargs = {
                "ssl_certfile": str(certfile),
                "ssl_keyfile":  str(keyfile),
                "ssl_ca_certs": str(cafile),
            }
        else:
            missing = [p.name for p in (certfile, keyfile, cafile) if not p.exists()]
            raise FileNotFoundError(f"SSL 启动失败，缺少文件: {', '.join(missing)}")
    else:
        print(f'操作系统为：windows')

    # ---------- ② 启动 Uvicorn ----------
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=Port.agent_fastapi_server,
        **ssl_kwargs                      # 非 Linux 或文件缺失时为空，自动回退到 HTTP
    )

