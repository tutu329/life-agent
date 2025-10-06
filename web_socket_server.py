import json
import asyncio
import websockets
import threading
from threading import Thread
import time
import ssl

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

    def start_server(self):
        self.thread = Thread(target=self._server_run, kwargs={'port': self.port})
        # self.thread = Thread(target=self._server_run, kwargs={'port': self.port}, daemon=True)
        self.thread.start()
        self.server_started = True
        # while True:
        #     time.sleep(1)
        self.thread.join()

    def _server_run(self, port):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def handler(websocket):
            dgreen(f'📱 新的WebSocket连接: {websocket.remote_address}')
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

        loop.run_until_complete(start_server())
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
                'formula':'E = m c^2',
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

def main():
    ws_server = Web_Socket_Server(port=5113)

    def _test():
        print('-----------------_test--------------------')
        ws_server._test_call_collabora_api()
        print('----------------/_test--------------------')

    thread = Thread(target=_test)
    thread.start()

    ws_server.start_server()

    thread.join()
    # ws_server._test_call_collabora_api()
    print('----------------------main() quit.----------------------')

if __name__ == "__main__":
    main()

