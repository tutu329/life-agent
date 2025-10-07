import json
import asyncio
import websockets
import threading
from threading import Thread
import time
import ssl

import asyncio, json, logging, uuid
from collections import defaultdict
from urllib.parse import urlsplit, parse_qs
from websockets.server import ServerConnection
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK, ConnectionClosedError


from typing import Any, Dict, Set, List, Literal, Optional, Union, Tuple, TYPE_CHECKING, Callable
from config import dred,dgreen,dblue,dyellow,dblack,dcyan,dmagenta, dwhite
from pprint import pprint
import config

DEBUG = config.Global.app_debug

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def dpprint(*args, **kwargs):
    if DEBUG:
        pprint(*args, **kwargs)

class Web_Socket_Server:
    def __init__(self, port=5113):  # 5113为测试port
        self.thread: Thread = None
        self.port = port
        self.server_started = False
        self.web_socket = None

        self.server = None  # websockets.serve()

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.clients:Set[ServerConnection] = set()

    def stop_server(self, timeout: float = 5.0):
        """优雅停止服务器并回收线程"""
        if self.server and self.loop:
            # 1) 关闭服务器：让 _server_run 里的 wait_closed() 返回
            self.loop.call_soon_threadsafe(self.server.close)
        # 2) 等待线程退出（_server_run 返回后线程会自己结束）
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)

    def start_server(self):
        self.thread = Thread(target=self._server_run, kwargs={'port': self.port})
        # self.thread = Thread(target=self._server_run, kwargs={'port': self.port}, daemon=True)
        self.thread.start()
        self.server_started = True

    def _server_run(self, port):
        async def handler(websocket):
            dgreen(f'📱 新的WebSocket连接: {websocket.remote_address}, type(websocket): {type(websocket)}')
            dgreen(f'websocket: {websocket}')
            self.clients.add(websocket)
            dred(f'clients: {self.clients}')
            self.web_socket = websocket

            try:
                async for message in websocket:
                    data = json.loads(message)
                    dgreen(f'data: {data}')
            except websockets.exceptions.ConnectionClosed as e:
                dprint(f'📱 WebSocket连接已关闭: {websocket.remote_address}')
            except Exception as e:
                dprint(f'⚠️ WebSocket连接错误: {websocket.remote_address} - {e}')

        async def start_server():
            print('----------------------start_server----------------------')
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
        print('----------------------server quit.----------------------')

    def send_command(self, command):
        """向指定客户端发送命令（同步接口）"""
        # 创建新的事件循环发送命令
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            success, message = loop.run_until_complete(self._async_send_command(command))
            return success, message
        except Exception as e:
            return False, f'发送失败: {e}'
        finally:
            loop.close()

    async def _async_send_command(self, command):
        try:
            command_json = json.dumps(command, ensure_ascii=False)
            await self.web_socket.send(command_json)
            # dgreen(f'_async_send_command()成功：client_id为"{client_id}".')
            return True, 'success'
        except Exception as e:
            return False, f'发送失败: {e}'

    def _test_call_collabora_api(self):
        print('------------------_test_call_collabora_api--------------------')
        while True:
            if self.web_socket:
                break

            time.sleep(0.1)

        if self.web_socket:
            # ------临时的websocket连接方式（选择第一个连接的客户端进行测试）------
            timeout = 30  # 等待30秒
            start_time = time.time()

            # 桥接collabora CODE接口
            command = {
                'type': 'office_operation',
                'operation': 'call_python_script',
                # 'agent_id': agent_id,
                # 'agent_id': top_agent_id,
                'data': {},
                'timestamp': int(time.time() * 1000)
            }
            # command = {
            #     'type': 'office_operation',
            #     'operation': 'call_python_script',
            #     # 'agent_id': agent_id,
            #     # 'agent_id': top_agent_id,
            #     'data': {},
            #     'timestamp': int(time.time() * 1000)
            # }
            params = {
                'formula':'E = m cdot c^{2} int from a to b f(x) dx = F(b) - F(a)',
                # 'formula':'int_{a}^{b}f(x)dx = F(b)-F(a)',
                # 'formula':'E = m c^2',
                'as_inline':True,
                'base_font_height':12,
            }
            # params = {
            #     'text':'hi every body4!\n hi every body5!',
            #     'font_name':'SimSun',
            #     'font_color':'blue',
            #     'font_size':12,
            # }
            command['data'] = {
                'cmd':'insert_math',
                'params':params
            }
            # command['data'] = {
            #     'cmd':'insert_text',
            #     'params':params
            # }

            # 通过web-socket发送至前端
            success, message = self.send_command(command)
            print(f'command={command!r}')
            print(f'success={success!r}, message={message!r}')
            print('-----------------/_test_call_collabora_api--------------------')
            return success, message

class Web_Socket_Server_Manager:
    server_pool:Dict[str, Web_Socket_Server] = {}   # port <--> ws_server

    @classmethod
    def start_server(cls, port)->Web_Socket_Server:
        server = Web_Socket_Server()
        server.start_server()
        cls.server_pool[port] = server

        return server

    @classmethod
    def stop_server(cls, port):
        server = cls.server_pool.pop(port)
        server.stop_server()

def main():
    ws_server = Web_Socket_Server_Manager.start_server(5113)

    def _test():
        print('-----------------_test--------------------')
        ws_server._test_call_collabora_api()
        print('----------------/_test--------------------')
        Web_Socket_Server_Manager.stop_server(5113)

    thread = Thread(target=_test)
    thread.start()

    # thread.join()
    # ws_server._test_call_collabora_api()
    print('----------------------main() quit.----------------------')

if __name__ == "__main__":
    main()

