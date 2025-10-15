# app/main.py
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

# 你现有模块
from agent.core.agent_manager import Agent_Manager   # 假设将你贴的代码保存为 agent_manager.py
from web_socket_server import Web_Socket_Server_Manager  # 如有
# from agent.tools.tool_manager import server_register_all_local_tool_on_start  # 如你需要

import config
from config import dred,dgreen,dcyan,dyellow,dblue,dblack,dwhite
from typing import Any, Dict, List, Set, Literal, Optional, Union, Tuple, TYPE_CHECKING, Callable
from pprint import pprint

from agent.core.mcp.protocol import MCP_Server_Request


DEBUG = True
# DEBUG = config.Global.app_debug

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def dpprint(*args, **kwargs):
    if DEBUG:
        pprint(*args, **kwargs)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --------- startup ----------
    # 1) 初始化本地工具（只做一次）
    try:
        local_tool_quests, local_tool_funcs = Agent_Manager.init()
        dprint("--------------所有local tools的信息------------------")
        for tool_param_dict in local_tool_quests:
            dprint(tool_param_dict)
        dprint("-------------/所有local tools的信息------------------")

        dprint("--------------指定tool_name的local tool的信息------------------")
        dprint(Agent_Manager.get_local_tool_names())
        dprint(Agent_Manager.get_local_tool_param_dict(tool_name='Write_Chapter_Tool'))
        dprint(Agent_Manager.get_local_tool_param_dict(tool_name='Folder_Tool'))
        dprint("-------------/指定tool_name的local tool的信息------------------")

        # dprint("--------------指定url的MCP的所有tool_name------------------")
        # url = "https://powerai.cc:8011/mcp/sqlite/sse"
        # dprint(f'url={url}')
        # dpprint(await Agent_Manager.get_mcp_url_tool_names_async(url))
        # # dpprint(Agent_Manager.get_mcp_url_tool_names("http://localhost:8789/sse"))
        #
        # # npx @playwright/mcp@latest --port 8788 --headless --browser chromium
        # url = "http://localhost:8788/sse"
        # dprint(f'url={url}')
        # dpprint(await Agent_Manager.get_mcp_url_tool_names_async(url))
        # dprint("-------------/指定url的MCP的所有tool_name------------------")

        # 如果你还有额外注册流程：
        # server_register_all_local_tool_on_start()
    except Exception as e:
        # 这里直接抛出可以让 uvicorn 启动失败，便于定位
        raise

    # 2) （可选）启动你自己的 WebSocket 子系统/守护线程
    # Web_Socket_Server_Manager.start_all_servers()  # 如需

    yield

    # --------- shutdown ----------
    try:
        # 1) 取消所有还在运行的 agent
        for agent_id, agent_data in list(Agent_Manager.agents_dict.items()):
            try:
                Agent_Manager.cancel_agent_run(agent_id)
            except Exception:
                pass
            # 等待一小会儿，避免强退
            th = Agent_Manager._get_thread(agent_id)
            if th and th.is_alive():
                th.join(timeout=3)

        # 2) 关闭子系统
        try:
            Web_Socket_Server_Manager.stop_all_servers()
        except Exception:
            pass
    except Exception:
        # 关停阶段尽量吞错误，避免影响进程退出
        pass

app = FastAPI(lifespan=lifespan)

# 路由
from agent.api.routers import agents
app.include_router(agents.router, prefix="/agents", tags=["agents"])

# CORS/鉴权请视情况在这里加

if __name__ == "__main__":
    import console

    port = config.Port.agents_api
    server_at = 'agent.api.main.py'
    info = f'Agents API server已启动(port:{port}, server_at:{server_at!r})...'
    console.server_output(info)

    uvicorn.run(
        app,
        host="0.0.0.0",                 # 监听所有网络接口
        port=port,                      # 指定端口8005
        # 其他可选参数：
        # reload=True,                  # 开发模式，代码改动自动重启
        # log_level="info",
    )
