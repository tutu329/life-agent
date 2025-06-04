from abc import ABC, abstractmethod

from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent.tools.base_tool import Base_Tool
from agent.tools.protocol import Action_Result, Tool_Call_Paras

class FastFPI_Remote_Tool_Register_Data(BaseModel):
    tool_class         :Base_Tool               # Base_Tool的子类
    path                :Optional[str] = None   # 工具path，如：'/Remote_Folder_Tool'

class FastAPI_Remote_Tool_Base(ABC):
    def __init__(
        self,
        register_data:FastFPI_Remote_Tool_Register_Data,
    ) -> None:
        self.tool_class = register_data.tool_class
        self.path = register_data.path

        self.router = APIRouter(tags=[self.tool_class.name])
        self._register()

    def _register(self) -> None:
        @self.router.post(
            path=self.path or '/'+self.tool_class.name,
            response_model=Action_Result,
            summary=self.tool_class.description
        )
        async def remote_tool(request:Tool_Call_Paras)->Action_Result:
            return self.tool_class.call(request)

    # 向fastapi的app注册
    def attach(self, app: FastAPI) -> None:
        app.include_router(self.router)

def create_fastapi_app(lifespan, title="Agent FastAPI Server") -> FastAPI:
    """返回完全配置好的 FastAPI 实例"""
    app = FastAPI(title="Agent API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app

# attach所有remote tools到app
def attach_all_remote_tools(app, remote_tool_instances: List[FastAPI_Remote_Tool_Base]) -> None:
    for r in remote_tool_instances:
        r.attach(app)