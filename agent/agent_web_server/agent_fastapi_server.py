from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from config import Port

# agent
from agent.agent_config import Config
from agent.tool_agent import Tool_Agent

# tools
from agent.tools.folder_tool import Folder_Tool
from agent.tools.human_console_tool import Human_Console_Tool

app = FastAPI(title="Agent FastAPI Server")

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

@app.get("/")
def root():
    return {"server status": "Agent FastAPI Server 运行中..."}

@app.post("/run_agent")
def run_agent(request: Agent_Request):
    """运行Agent"""
    # 创建工具列表
    tools = [Human_Console_Tool, Folder_Tool]

    # 创建配置
    config = Config(
        base_url=request.base_url,
        api_key=request.api_key
    )

    # 创建并运行Agent
    agent = Tool_Agent(
        query=request.query,
        tool_classes=tools,
        agent_config=config
    )

    # 初始化和运行
    agent.init()
    success = agent.run()

    return {
        "success": success,
        "query": request.query
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=Port.agent_fastapi_server)
