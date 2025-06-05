from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
import uvicorn

import asyncio
import json

from config import Port

# agent
from agent.tools.tool_manager import server_register_all_local_tool_on_start
from agent.core.agent_config import Agent_Config
from agent.core.tool_agent import Tool_Agent
from contextlib import asynccontextmanager
from agent.tools.protocol import Action_Result, Tool_Call_Paras
# from agent.core.legacy_protocol import Action_Result
from dataclasses import dataclass, field, asdict

# tools
from agent.tools.folder_tool import Folder_Tool
from agent.tools.human_console_tool import Human_Console_Tool

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

class Agent_Request(BaseModel):
    query: str
    base_url: str = "http://powerai.cc:28001/v1"
    api_key: str = "empty"
    llm_model_id: str = ""

@app.get("/")
def root():
    return {"server status": "Agent FastAPI Server 运行中..."}

@app.post("/run_agent_sync")
def run_agent_sync(request: Agent_Request):
    """运行Agent"""
    # 创建工具列表
    tools = [Human_Console_Tool, Folder_Tool]

    # 创建配置
    config = Agent_Config(
        base_url=request.base_url,
        api_key=request.api_key,
        model_id=request.llm_model_id
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
async def run_agent_stream(request: Agent_Request):
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

from agent.agent_web_server.protocol import FastAPI_Agent_Endpoint
@FastAPI_Agent_Endpoint(app)
async def start_agent_stream(request: Agent_Request):
    import time
    from agent.tools.tool_manager import print_all_registered_tools, server_register_all_local_tool_on_start, \
        server_register_remote_tool_dynamically, Registered_Remote_Tool_Data

    from agent.core.multi_agent_server import server_start_register_2_levels_agents_system, print_agent_status
    from agent.core.multi_agent_server import __server_wait_registered_agent

    # --------注册一个远程tool(需要远程开启该tool call的fastapi)--------
    # 注册local所有tool
    server_register_all_local_tool_on_start()
    reg_data = Registered_Remote_Tool_Data(
        name="Remote_Folder_Tool",
        description="返回远程服务器上指定文件夹下所有文件和文件夹的名字信息。",
        parameters=[
            {
                "name": "file_path",
                "type": "string",
                "description": "本参数为文件夹所在的路径",
                "required": "True",
            }
        ],
        endpoint_url="http://localhost:5120/remote_folder_tool",
        method="POST",
        timeout=15,
    )
    tool_id = server_register_remote_tool_dynamically(reg_data)
    print_all_registered_tools()
    # -------/注册一个远程tool(需要远程开启该tool call的fastapi)--------

    query = r'我叫土土，请告诉我当前文件夹下有哪些文件'
    config = Agent_Config(
        base_url='https://api.deepseek.com/v1',
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        model_id='deepseek-chat',  # 模型指向 DeepSeek-V3-0324
    )
    upper_agent_dict = {
        'tool_names': ['Human_Console_Tool'],
        'exp_json_path': 'my_2_levels_mas_exp.json',
        'agent_config': config,
    }
    lower_agents_as_tool_dict_list = [
        {
            'tool_names': ['Human_Console_Tool', 'Remote_Folder_Tool'],
            'agent_config': config,
            'as_tool_name': 'Folder_Agent_As_Tool',
            'as_tool_description': '本工具用于获取文件夹中的文件和文件夹信息'
        }
    ]
    agent_id = server_start_register_2_levels_agents_system(
        query=query,
        upper_agent_dict=upper_agent_dict,
        lower_agents_as_tool_dict_list=lower_agents_as_tool_dict_list
    )

    time.sleep(0.5)
    print_agent_status(agent_id)
    __server_wait_registered_agent(agent_id, timeout_second=20000000)

    # server_continue_agent(agent_id, query='我刚才告诉你我叫什么？')
    # print_agent_status(agent_id)


if __name__ == "__main__":
    from agent.agent_web_server.protocol import fastapi_show_all_routes
    fastapi_show_all_routes(app)
    uvicorn.run(app, host="0.0.0.0", port=Port.agent_fastapi_server)
