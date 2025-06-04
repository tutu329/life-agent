import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from config import Port
from agent.agent_web_client.protocol import create_fastapi_app, attach_all_remote_tools

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时的一次性初始化
    print(f'Remote Tool的FastAPI Server启动全局一次性初始化。')
    # ...
    yield
    # 关闭时清理（如close/shutdown之类）

app = create_fastapi_app(lifespan=lifespan, title="Agent FastAPI Server")


# 将需要的FastAPI_Remote_Tool类的所有实例，都进行注册
def register_remote_tools_on_start():
    # -----------------------------------修改为你所需FastAPI_Remote_Tool类的实例-----------------------------------
    from agent.agent_web_client.fastapi_remote_tools.remote_folder_tool import Remote_Folder_Tool_Example

    remote_tool_instances = [
        Remote_Folder_Tool_Example(),
    ]
    # ----------------------------------/修改为你所需FastAPI_Remote_Tool类的实例-----------------------------------
    return remote_tool_instances

def main():
    attach_all_remote_tools(app, register_remote_tools_on_start())
    uvicorn.run(app, host="0.0.0.0", port=Port.agent_fastapi_server)

if __name__ == "__main__":
    main()