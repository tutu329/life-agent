
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

class Web_Socket_Manager:
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

    def start_server(self, port=5112):
        """启动WebSocket服务器"""
        print(f'🔍 WebSocket服务器状态检查: server_started={self.server_started}')

        if self.server_started:
            print('⚠️ WebSocket服务器已运行，跳过启动')
            return

        if self.server_thread is None or not self.server_thread.is_alive():
            print('🚀 启动新的WebSocket服务器线程...')
            self.server_thread = threading.Thread(target=self._run_server, kwargs={'port': port}, daemon=True)
            self.server_thread.start()
            print('🚀 WebSocket服务器启动中... (端口:5112)')
            self.server_started = True
            time.sleep(1)
        else:
            print('⚠️ WebSocket服务器线程已存在且运行中')
            self.server_started = True

    def _run_server(self, port=5112):
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
                        if client_id in self.connections:
                            print(f'🗑️ 清理断开连接: {client_id}')
                            del self.connections[client_id]
                        if websocket in self.connection_reverse:
                            del self.connection_reverse[websocket]
                        print(f'🔍 剩余连接数: {len(self.connections)}')

        async def start_server(port=port):
            import ssl
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            try:
                ssl_context.load_cert_chain('/home/tutu/ssl/powerai_public.crt', '/home/tutu/ssl/powerai.key')
                self.server = await websockets.serve(handler, '0.0.0.0', port, ssl=ssl_context)
                print(f'✅ WebSocket服务器已启动 (WSS端口:{port})')
                await self.server.wait_closed()
            except FileNotFoundError:
                print('⚠️ SSL证书未找到，使用普通WebSocket连接')
                self.server = await websockets.serve(handler, '0.0.0.0', port)
                print(f'✅ WebSocket服务器已启动 (WS端口:{port})')
                await self.server.wait_closed()
            except Exception as e:
                print(f'❌ SSL WebSocket启动失败: {e}，回退到普通连接')
                try:
                    self.server = await websockets.serve(handler, '0.0.0.0', port)
                    print(f'✅ WebSocket服务器已启动 (WS端口:{port})')
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
    manager = Web_Socket_Manager()
    print(f'🔧 获取WebSocket管理器实例: {id(manager)} (server_started={manager.server_started})')
    return manager