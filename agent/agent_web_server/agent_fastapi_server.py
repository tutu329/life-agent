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





# 通用WebSocket管理器 - 可被多个模块使用
# 提供WebSocket服务器和消息发送功能

import json
import asyncio
import websockets
import threading
import time
from utils.encode import safe_encode
from agent.tools.base_tool import Base_Tool
from agent.tools.protocol import Action_Result, Tool_Call_Paras


# 通用WebSocket管理器 - 可被多个模块使用
# 提供WebSocket服务器和消息发送功能

class WebSocket_Manager:
    """通用WebSocket管理器单例类"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.server = None
        self.server_thread = None
        self.connections = {}  # id -> websocket连接的映射
        self.connection_reverse = {}  # websocket连接 -> id的反向映射
        self.server_started = False
        self.connection_lock = threading.Lock()
        print('🔧 WebSocket_Manager 单例已初始化')

    def start_server(self):
        """启动WebSocket服务器"""
        print(f'🔍 WebSocket服务器状态检查: server_started={self.server_started}')

        if self.server_started:
            print('⚠️ WebSocket服务器已运行，跳过启动')
            return

        if self.server_thread is None or not self.server_thread.is_alive():
            print('🚀 启动新的WebSocket服务器线程...')
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            print('🚀 WebSocket服务器启动中... (端口:5112)')
            self.server_started = True
            time.sleep(1)
        else:
            print('⚠️ WebSocket服务器线程已存在且运行中')
            self.server_started = True

    def _run_server(self):
        """运行WebSocket服务器"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def handler(websocket):
            print(f'📱 新的WebSocket连接: {websocket.remote_address}')

            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get('type') == 'register' and data.get('agent_id'):
                            client_id = data['agent_id']

                            with self.connection_lock:
                                # 清理旧连接
                                if websocket in self.connection_reverse:
                                    old_id = self.connection_reverse[websocket]
                                    if old_id in self.connections:
                                        print(f'🗑️ 删除旧连接: {old_id}')
                                        del self.connections[old_id]

                                # 注册新连接
                                print(f'➕ 注册新连接: {client_id}')
                                self.connections[client_id] = websocket
                                self.connection_reverse[websocket] = client_id
                                print(f'🔍 当前连接数: {len(self.connections)}')

                            # 发送注册成功确认
                            await websocket.send(json.dumps({
                                'type': 'register_success',
                                'agent_id': client_id,
                                'message': 'WebSocket连接已注册'
                            }))
                        else:
                            print(f'⚠️ 收到无效消息: {data}')
                    except json.JSONDecodeError:
                        print(f'⚠️ 收到非JSON消息: {message}')

            except websockets.exceptions.ConnectionClosed as e:
                print(f'📱 WebSocket连接已关闭: {websocket.remote_address}')
            except Exception as e:
                print(f'⚠️ WebSocket连接错误: {websocket.remote_address} - {e}')
            finally:
                # 清理连接映射
                with self.connection_lock:
                    if websocket in self.connection_reverse:
                        client_id = self.connection_reverse[websocket]
                        print(f'🗑️ 清理断开连接: {client_id}')
                        del self.connections[client_id]
                        del self.connection_reverse[websocket]
                        print(f'🔍 剩余连接数: {len(self.connections)}')

        async def start_server():
            import ssl
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            try:
                ssl_context.load_cert_chain('/home/tutu/ssl/powerai_public.crt', '/home/tutu/ssl/powerai.key')
                self.server = await websockets.serve(handler, '0.0.0.0', 5112, ssl=ssl_context)
                print('✅ WebSocket服务器已启动 (WSS端口:5112)')
                await self.server.wait_closed()
            except FileNotFoundError:
                print('⚠️ SSL证书未找到，使用普通WebSocket连接')
                self.server = await websockets.serve(handler, '0.0.0.0', 5112)
                print('✅ WebSocket服务器已启动 (WS端口:5112)')
                await self.server.wait_closed()
            except Exception as e:
                print(f'❌ SSL WebSocket启动失败: {e}，回退到普通连接')
                try:
                    self.server = await websockets.serve(handler, '0.0.0.0', 5112)
                    print('✅ WebSocket服务器已启动 (WS端口:5112)')
                    await self.server.wait_closed()
                except Exception as fallback_error:
                    print(f'❌ WebSocket服务器启动完全失败: {fallback_error}')

        loop.run_until_complete(start_server())

    def send_command(self, client_id, command):
        """向指定客户端发送命令（同步接口）"""
        # 创建新的事件循环发送命令
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            success, message = loop.run_until_complete(self._async_send_command(client_id, command))
            return success, message
        except Exception as e:
            return False, f'发送失败: {e}'
        finally:
            loop.close()

    async def _async_send_command(self, client_id, command):
        """向指定客户端发送命令（异步实现）"""
        with self.connection_lock:
            if client_id not in self.connections:
                return False, f'客户端 {client_id} 没有WebSocket连接'

            websocket = self.connections[client_id]

        try:
            command_json = json.dumps(command, ensure_ascii=False)
            await websocket.send(command_json)
            return True, 'success'
        except Exception as e:
            # 连接可能已断开，清理映射
            with self.connection_lock:
                if client_id in self.connections:
                    print(f'🗑️ 发送失败，清理连接: {client_id}')
                    del self.connections[client_id]
                if websocket in self.connection_reverse:
                    del self.connection_reverse[websocket]
            return False, f'发送失败: {e}'

    def get_connected_clients(self):
        """获取已连接的客户端列表"""
        with self.connection_lock:
            return list(self.connections.keys())


def get_websocket_manager():
    """获取WebSocket管理器单例实例"""
    manager = WebSocket_Manager()
    print(f'🔧 获取WebSocket管理器实例: {id(manager)} (server_started={manager.server_started})')
    return manager









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

class Query_Agent_Request(BaseModel):
    agent_id    : str
    query       : str   # 如：'当前文件夹下有哪些文件'

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

# @FastAPI_Endpoint_With_SSE(
#     app=app,
#     return_type=Registered_Agent_Data,
#     return_id_name='agent_id',
#     return_stream_queues_name='agent_stream_queues',
# )
# async def start_2_level_agents_stream(request: Agent_Request):
#     import time
#     from agent.tools.tool_manager import print_all_registered_tools, server_register_all_local_tool_on_start, \
#         server_register_remote_tool_dynamically, Registered_Remote_Tool_Data
#
#     from agent.core.multi_agent_server import server_start_and_register_2_levels_agents_system, print_agent_status
#     from agent.core.multi_agent_server import __server_wait_registered_agent
#     from config import Port
#
#     dblue(f'--------------------------start_2_level_agents_stream获得request参数--------------------------------')
#     dblue(request)
#     dblue(f'-------------------------/start_2_level_agents_stream获得request参数--------------------------------')
#
#     # --------注册一个远程tool(需要远程开启该tool call的fastapi)--------
#     # 注册local所有tool
#     server_register_all_local_tool_on_start()
#     reg_data = Registered_Remote_Tool_Data(
#         name="Remote_Folder_Tool",
#         description="返回远程服务器上指定文件夹下所有文件和文件夹的名字信息。",
#         parameters=[
#             {
#                 "name": "dir",
#                 "type": "string",
#                 "description": "本参数为文件夹所在的路径",
#                 "required": "True",
#             }
#         ],
#         endpoint_url=f"http://localhost:{Port.remote_tool_fastapi_server}/Folder_Tool",
#         method="POST",
#         timeout=15,
#     )
#     tool_id = server_register_remote_tool_dynamically(reg_data)
#     print_all_registered_tools()
#     # -------/注册一个远程tool(需要远程开启该tool call的fastapi)--------
#
#     query = r'我叫电力用户，请告诉./文件夹下有哪些文件'
#     config = Agent_Config(
#         **(request.agent_config.dict())
#         # base_url='https://api.deepseek.com/v1',
#         # api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
#         # llm_model_id = 'deepseek-reasoner',  # 模型指向 DeepSeek-R1-0528
#         # llm_model_id='deepseek-chat',  # 模型指向 DeepSeek-V3-0324
#     )
#     upper_agent_dict = {
#         'tool_names': ['Human_Console_Tool'],
#         'exp_json_path': 'my_2_levels_mas_exp.json',
#         'agent_config': config,
#     }
#     lower_agents_as_tool_dict_list = [
#         {
#             'tool_names': ['Human_Console_Tool', 'Remote_Folder_Tool'],
#             'agent_config': config,
#             'as_tool_name': 'Folder_Agent_As_Tool',
#             'as_tool_description': '本工具用于获取文件夹中的文件和文件夹信息'
#         }
#     ]
#     agent_data = server_start_and_register_2_levels_agents_system(
#         query=query,
#         upper_agent_dict=upper_agent_dict,
#         lower_agents_as_tool_dict_list=lower_agents_as_tool_dict_list
#     )
#
#     time.sleep(0.5)
#     print_agent_status(agent_data.agent_id)
#
#     return agent_data
#
#     # __server_wait_registered_agent(agent_id, timeout_second=20000000)
#
#     # server_continue_agent(agent_id, query='我刚才告诉你我叫什么？')
#     # print_agent_status(agent_id)

# @FastAPI_Endpoint_With_SSE(
#     app=app,
#     return_type=Registered_Agent_Data,
#     return_id_name='agent_id',
#     return_stream_queues_name='agent_stream_queues',
# )
# async def start_2_level_agents_stream(request: Agent_Request):
#     import time
#     from agent.tools.tool_manager import print_all_registered_tools, server_register_all_local_tool_on_start, \
#         server_register_remote_tool_dynamically, server_register_remote_tools_dynamically, Registered_Remote_Tool_Data
#
#     from agent.core.multi_agent_server import server_start_and_register_2_levels_agents_system, print_agent_status
#     from agent.core.multi_agent_server import __server_wait_registered_agent
#     from config import Port
#
#     dblue(f'--------------------------start_2_level_agents_stream获得request参数--------------------------------')
#     dblue(request)
#     dblue(f'-------------------------/start_2_level_agents_stream获得request参数--------------------------------')
#
#     # --------注册一个远程tool(需要远程开启该tool call的fastapi)--------
#     # 注册local所有tool
#     server_register_all_local_tool_on_start()
#     tool_ids = server_register_remote_tools_dynamically(request.remote_tools)
#     print_all_registered_tools()
#     # -------/注册一个远程tool(需要远程开启该tool call的fastapi)--------
#
#     agent_data = server_start_and_register_2_levels_agents_system(
#         query=request.query,
#         upper_agent_config=request.upper_agent_config,
#         lower_agents_config=request.lower_agents_config
#     )
#
#     time.sleep(0.5)
#     print_agent_status(agent_data.agent_id)
#
#     return agent_data
#
#     # __server_wait_registered_agent(agent_id, timeout_second=20000000)
#
#     # server_continue_agent(agent_id, query='我刚才告诉你我叫什么？')
#     # print_agent_status(agent_id)

@app.post("/api/get_agent_status")
async def get_agent_status(request:Agent_Status_Request):
    agent_status = server_get_agent_status(agent_id=request.agent_id)
    return agent_status

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
    server_register_all_local_tool_on_start()
    tool_ids = server_register_remote_tools_dynamically(request.remote_tools)
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
    agent_data = server_continue_agent(agent_id=request.agent_id, query=request.query)
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

