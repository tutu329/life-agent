import json
import asyncio
import websockets
import threading
from threading import Thread
import time
import ssl

import asyncio, json, logging
from uuid import uuid4
from collections import defaultdict
from urllib.parse import urlsplit, parse_qs
from websockets.server import ServerConnection
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK, ConnectionClosedError
from pydantic import BaseModel, Field, ConfigDict


from typing import Any, Dict, Set, List, Literal, Optional, Union, Tuple, TYPE_CHECKING, Callable
from config import dred,dgreen,dblue,dyellow,dblack,dcyan,dmagenta, dwhite
from pprint import pprint
import config
import console

DEBUG = config.Global.app_debug

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def dpprint(*args, **kwargs):
    if DEBUG:
        pprint(*args, **kwargs)

class Connection_Info(BaseModel):
    user_id: str = ''               # user_id
    client_id: str = ''             # client_id(临时连接的id)

class Web_Socket_Client_Register_Response(BaseModel):
    client_id: str
    client_id_generated_by_server: bool   # client_id是否由server生成

# 主要用于远程client，client在ws.onopen()中通过ws.send()进行注册时需遵循
class Web_Socket_Client_Register_Request(BaseModel):
    type: str = 'register'
    client_id: str = ''     # client_id可以是agent_id这类从server应用层获取的id，并由client指定给web_socket_server(若不指定client_id，则由server的uuid4生成)

class Web_Socket_Server:
    def __init__(self, port):
        self.thread: Thread = None
        self.port = port
        self.server_started = False

        self.server = None  # websockets.serve()

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # connections的管理
        self.connections:Dict[ServerConnection, Connection_Info] = {}   # 1 server <--> m connections, n connections <--> user_id
        # connections中client的筛选(这里的client_id不是应用层面user一一对应的client_id，只是应用层user的某个临时连接id)
        self.registered_client:Dict[str, ServerConnection] = {}         # 1 client_id <--> 1 connection, 1 user <--> n client_id

    def stop_server(self, timeout: float = 5.0):
        """优雅停止服务器并回收线程"""
        if self.server and self.loop:
            # 1) 关闭服务器：让 _server_run 里的 wait_closed() 返回
            self.loop.call_soon_threadsafe(self.server.close)
        # 2) 等待线程退出（_server_run 返回后线程会自己结束）
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)

        self.server_started = False

    def start_server(self):
        if not self.server_started:
            self.thread = Thread(target=self._server_run, kwargs={'port': self.port})
            # self.thread = Thread(target=self._server_run, kwargs={'port': self.port}, daemon=True)
            self.thread.start()
            self.server_started = True

    def register_client(self, client_id:str, connection:ServerConnection):
        self.registered_client[client_id] = connection

    def unregister_client(self, client_id:str):
        self.registered_client.pop(client_id, None)

    def print_connections(self):
        dgreen(f'-----------------Web_Socket_Server(Port={self.port}) connections----------------------')
        for k, v in self.connections.items():
            dblue(f'client_info: {v}, connection: {k}')
        dgreen(f'----------------/Web_Socket_Server(Port={self.port}) connections----------------------')

    async def broadcast(self, data: Any):
        for connection, connection_info in self.connections.items():
            await connection.send(data)

    async def send_client(self, client_id:str, data: Any):
        dyellow(f'self.connections: {self.connections}')
        dyellow(f'self.registered_client: {self.registered_client}')
        for connection, connection_info in self.connections.items():
            reg_conn = self.registered_client.get(client_id)
            if reg_conn and reg_conn==connection:
                dgreen(f'Web_Socket_Server.send_client发送成功(client_id={client_id!r}, data={data}, connection={connection}).')
                await connection.send(data)
                return
        # for connection, connection_info in self.connections.items():
        #     for reg_client_id, reg_connection in self.registered_client.items():
        #         if connection == reg_connection:
        #             dgreen(f'Web_Socket_Server.send_client发送成功(client_id={client_id!r}, data={data}, connection={connection}).')
        #             await connection.send(data)
        #             return

        dred(f'Web_Socket_Server.send_client发送失败(client_id={client_id!r}, data={data}).')

    def _server_run(self, port):
        async def handler(conn):
            dgreen(f'📱 新的WebSocket连接: {conn.remote_address}')
            connection_info = Connection_Info()
            self.connections[conn] = connection_info

            self.print_connections()

            try:
                async for message in conn:
                    data = json.loads(message)

                    # --------------------client在on-open时，会发register信息-----------------------
                    # 注册data为Web_Socket_Client_Register_Request格式：{'type': 'register', 'client_id': '5113_ws_client'}
                    dgreen(f'【Web_Socket_Server.handler()】data: {data}')
                    if 'type' in data and data['type']=='register' and 'client_id' in data:
                        client_id = data['client_id']

                        # 将client_id反馈给client
                        if not client_id:
                            # 若client没有提供client_id，为''，则生成唯一client_id，并
                            client_id = str(uuid4())
                            res = Web_Socket_Client_Register_Response(client_id=client_id, client_id_generated_by_server=True)
                            await conn.send(json.dumps(res.model_dump(), ensure_ascii=False))
                            dred(f'【Web_Socket_Server.handler()】conn.send: client_id={client_id!r}, client_id_generated_by_server={res.client_id_generated_by_server}')
                        else:
                            res = Web_Socket_Client_Register_Response(client_id=client_id, client_id_generated_by_server=False)
                            await conn.send(json.dumps(res.model_dump(), ensure_ascii=False))
                            dred(f'【Web_Socket_Server.handler()】conn.send: client_id={client_id!r}, client_id_generated_by_server={res.client_id_generated_by_server}')

                        # 在server注册client_id和connection
                        self.register_client(client_id, conn)
                        connection_info.client_id = client_id
                        self.print_connections()

                        # dgreen(f'-------------------client_id={client_id!r} registered------------------------')
                        # dblue(self.registered_client)
                        # dgreen(f'------------------/client_id={client_id!r} registered------------------------')
                        # time.sleep(1) # 防止后续的send_client()失败
                    # -------------------/client在on-open时，会发register信息-----------------------

            except websockets.exceptions.ConnectionClosed as e:
                dprint(f'📱 WebSocket连接已关闭: {conn.remote_address}')
                self.connections.pop(conn, None)
                self.print_connections()
            except Exception as e:
                dprint(f'⚠️ WebSocket连接错误: {conn.remote_address} - {e}')

        async def start_server():
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            try:
                ssl_context.load_cert_chain('/home/tutu/ssl/powerai_public.crt', '/home/tutu/ssl/powerai.key')
                self.server = await websockets.serve(handler, '0.0.0.0', port, ssl=ssl_context)
                dprint(f'✅ WebSocket服务器已启动 (WSS端口:{port})')
                await self.server.wait_closed()
            except Exception as e:
                dprint(f'❌ SSL WebSocket启动失败: {e}，回退到普通连接')
                try:
                    self.server = await websockets.serve(handler, '0.0.0.0', port)
                    dprint(f'✅ WebSocket服务器已启动 (WS端口:{port})')
                    await self.server.wait_closed()
                except Exception as fallback_error:
                    dprint(f'❌ WebSocket服务器启动完全失败: {fallback_error}')

        self.loop.run_until_complete(start_server())
        # print('oops!')

class Web_Socket_Server_Manager:
    server_pool:Dict[str, Web_Socket_Server] = {}   # port <--> ws_server

    @classmethod
    def start_server(cls,
                     port,
                     server_at=''   # 如："office_tool.py"
                     ) -> Web_Socket_Server:
        if port not in cls.server_pool:
            server = Web_Socket_Server(port=port)
            server.start_server()
            cls.server_pool[port] = server
            info = f'Web_Socket_Server已启动(port:{port}, server_at:{server_at!r})...'
            console.server_startup_output(info)

            return server
        else:
            info = f'Web_Socket_Server(port:{port})已有，不再新建, server_at:{server_at!r})...'
            console.server_startup_output(info)
            return cls.server_pool[port]

    @classmethod
    def stop_server(cls, port):
        if port in cls.server_pool:
            server = cls.server_pool.pop(port)
            server.stop_server()
            dgreen(f'Web_Socket_Server已停止(port:{port})')

def main():
    port = 5113
    # port = 5112
    ws_server = Web_Socket_Server_Manager.start_server(port=port)
    ws_server = Web_Socket_Server_Manager.start_server(port=port)
    time.sleep(3)
    # Web_Socket_Server_Manager.stop_server(port=port)

if __name__ == "__main__":
    # print(len({}))
    # print(len({'a':['b','cc'], 'aa':[]}))
    # print('a1' in {'a':['b','cc'], 'aa':[]})
    # if {'a':33}:
    #     print(1)
    # else:
    #     print(2)
    main()

