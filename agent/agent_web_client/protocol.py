from abc import ABC, abstractmethod

from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, ConfigDict
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent.tools.base_tool import Base_Tool
from agent.tools.protocol import Action_Result, Tool_Call_Paras

class FastFPI_Remote_Tool_Register_Data(BaseModel):
    tool    :Base_Tool              # Base_Tool的子类实例
    path    :Optional[str] = None   # 工具path，如：'/Remote_Folder_Tool'

    # 开启“任意类型”支持
    model_config = ConfigDict(arbitrary_types_allowed=True)

class FastAPI_Remote_Tool_Base():
    def __init__(
        self,
        register_data:FastFPI_Remote_Tool_Register_Data,
    ) -> None:
        self.tool = register_data.tool
        self.path = register_data.path

        self.router = APIRouter(tags=[self.tool.name])
        self._register()

    def _register(self) -> None:
        @self.router.post(
            path=self.path or '/'+self.tool.name,
            response_model=Action_Result,
            summary=self.tool.description
        )
        async def remote_tool(request:Tool_Call_Paras)->Action_Result:
            path_str = self.path or '/' + self.tool.name
            print(f'path: "{path_str}"')
            return self.tool.call(request)

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
def attach_all_remote_tools(
        app:FastAPI,
        remote_tool_instances: List[FastAPI_Remote_Tool_Base]
) -> None:
    for r in remote_tool_instances:
        r.attach(app=app)
    fastapi_show_all_routes(app)

# 显示所有挂载的路由、以及GET/POST情况
def fastapi_show_all_routes(app: FastAPI):
    print(f'--------------------FastAPI服务器所挂载的所有路由-----------------------------')
    for r in app.routes:
        if hasattr(r, 'methods'):
            print(f'{list(r.methods)} {r.path}')
    print(f'-------------------/FastAPI服务器所挂载的所有路由-----------------------------')
