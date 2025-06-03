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
from agent.tools.tool_manager import server_register_all_tool
from agent.core.agent_config import Config
from agent.core.tool_agent import Tool_Agent
from contextlib import asynccontextmanager

# tools
from agent.tools.folder_tool import Folder_Tool
from agent.tools.human_console_tool import Human_Console_Tool

from config import dyellow


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ★ 启动时初始化 ★
    # 例如：一次性加载 LLM 或建立数据库池

    # 初始化agent和tool的注册
    registered_tools_dict = server_register_all_tool()

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
    model_id: str = ""

@app.get("/")
def root():
    return {"server status": "Agent FastAPI Server 运行中..."}

@app.post("/run_agent_sync")
def run_agent_sync(request: Agent_Request):
    """运行Agent"""
    # 创建工具列表
    tools = [Human_Console_Tool, Folder_Tool]

    # 创建配置
    config = Config(
        base_url=request.base_url,
        api_key=request.api_key,
        model_id=request.model_id
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


# -----------------------------用于remote_tool_call测试--------------------------------
from utils.encode import safe_encode
from utils.folder import get_folder_all_items_string

class Remote_Tool_Request(BaseModel):
    file_path: str

@app.post("/remote_tool_call")
async def remote_tool_call(request: Remote_Tool_Request):
    result_str = safe_encode(get_folder_all_items_string(directory=request.file_path))
    return {
        "success": False,
        "file_path": request.file_path,
        "result_str": result_str
    }
# ----------------------------/用于remote_tool_call测试--------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=Port.agent_fastapi_server)
