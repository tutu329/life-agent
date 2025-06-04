from typing import List, Dict, Any, Optional, Callable
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
import os, pathlib

from config import Port
from agent.tools.tool_manager import server_register_all_local_tool_on_start
from agent.tools.protocol import Action_Result, Tool_Call_Paras

from agent.agent_web_client.protocol import FastFPI_Remote_Tool_Register_Data, FastAPI_Remote_Tool_Base
from agent.agent_web_client.protocol import create_fastapi_app, attach_all_remote_tools

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时的一次性初始化
    print(f'Remote Tool的FastAPI Server已初始化。')
    # ...
    yield
    # 关闭时清理（如close/shutdown之类）

app = create_fastapi_app(lifespan=lifespan, title="Agent FastAPI Server")

remote_tool_instances = []

def main():
    attach_all_remote_tools(app, remote_tool_instances)
    uvicorn.run(app, host="0.0.0.0", port=Port.agent_fastapi_server)

if __name__ == "__main__":
    main()