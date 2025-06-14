# Office 控件操作工具 - 通过 WebSocket 与前端 EditorPanel 通信
# 控制 Collabora CODE 进行文档编辑操作

import json
import asyncio
import websockets
import threading
import time
from utils.encode import safe_encode
from agent.tools.base_tool import Base_Tool
from agent.tools.protocol import Action_Result, Tool_Call_Paras


# 全局WebSocket服务器管理器（单例模式）
class OfficeWebSocketManager:
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
        self.agent_connections = {}  # agent_id -> websocket连接的映射
        self.connection_agents = {}  # websocket连接 -> agent_id的反向映射
        self.server_started = False
        print('🔧 OfficeWebSocketManager 单例已初始化')

    def start_server(self):
        """启动WebSocket服务器"""
        print(f'🔍 OfficeWebSocketManager 单例状态检查: server_started={self.server_started}')

        if self.server_started:
            print('⚠️ WebSocket服务器已运行，跳过启动')
            return

        # 检查端口是否被占用
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('127.0.0.1', 5112))
            if result == 0:
                print('⚠️ 端口5112已被其他进程占用，可能是另一个Office WebSocket服务器实例')
                print('🔍 假设该服务器正常运行，跳过启动新实例')
                self.server_started = True  # 标记为已启动，避免重复尝试
                return

        if self.server_thread is None or not self.server_thread.is_alive():
            print('🚀 启动新的WebSocket服务器线程...')
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            print('🚀 全局WebSocket服务器启动中... (端口:5112)')
            self.server_started = True
            time.sleep(1)
        else:
            print('⚠️ WebSocket服务器线程已存在且运行中')

    def _run_server(self):
        """运行WebSocket服务器"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def handler(websocket):
            # async def handler(websocket, path):
            print(f'📱 新的WebSocket连接: {websocket.remote_address}')

            try:
                # 持续监听客户端消息，支持重新注册
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get('type') == 'register' and data.get('agent_id'):
                            new_agent_id = data['agent_id']

                            # 如果这个WebSocket之前注册过其他agent_id，先清理旧的映射
                            if websocket in self.connection_agents:
                                old_agent_id = self.connection_agents[websocket]
                                if old_agent_id in self.agent_connections:
                                    print(f'🗑️ 删除旧Agent连接: {old_agent_id}')
                                    del self.agent_connections[old_agent_id]
                                    print(f'🔍 删除后agent_connections: {list(self.agent_connections.keys())}')
                                print(f'🔄 WebSocket连接从Agent {old_agent_id} 重新注册到 {new_agent_id}')

                            # 注册新的连接
                            print(f'➕ 添加新Agent连接: {new_agent_id}')
                            self.agent_connections[new_agent_id] = websocket
                            self.connection_agents[websocket] = new_agent_id
                            print(f'🔍 添加后agent_connections: {list(self.agent_connections.keys())}')
                            print(f'✅ Agent {new_agent_id} 已注册WebSocket连接')

                            # 发送注册成功确认
                            await websocket.send(json.dumps({
                                'type': 'register_success',
                                'agent_id': new_agent_id,
                                'message': 'WebSocket连接已注册'
                            }))
                        else:
                            print(f'⚠️ 收到无效的消息: {data}')
                    except json.JSONDecodeError:
                        print(f'⚠️ 收到非JSON消息: {message}')

            except websockets.exceptions.ConnectionClosed:
                print(f'📱 WebSocket连接已关闭: {websocket.remote_address}')

            except Exception as e:
                print(f'⚠️ WebSocket连接错误: {e}')
            finally:
                # 清理连接映射
                if websocket in self.connection_agents:
                    agent_id = self.connection_agents[websocket]
                    print(f'🗑️ 清理断开的Agent连接: {agent_id}')
                    print(f'🔍 清理前agent_connections: {list(self.agent_connections.keys())}')
                    del self.agent_connections[agent_id]
                    del self.connection_agents[websocket]
                    print(f'🔍 清理后agent_connections: {list(self.agent_connections.keys())}')
                    print(f'📱 Agent {agent_id} WebSocket连接已断开')

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

    async def send_to_agent(self, agent_id, command):
        """向指定agent发送命令"""
        if agent_id not in self.agent_connections:
            return False, f'Agent {agent_id} 没有WebSocket连接'

        websocket = self.agent_connections[agent_id]
        try:
            command_json = json.dumps(command, ensure_ascii=False)
            await websocket.send(command_json)
            return True, 'success'
        except Exception as e:
            # 连接可能已断开，清理映射
            print(f'🗑️ 发送失败，清理Agent连接: {agent_id}')
            print(f'🔍 清理前agent_connections: {list(self.agent_connections.keys())}')
            if websocket in self.connection_agents:
                del self.connection_agents[websocket]
            del self.agent_connections[agent_id]
            print(f'🔍 清理后agent_connections: {list(self.agent_connections.keys())}')
            return False, f'发送失败: {e}'

    def get_connected_agents(self):
        """获取已连接的agent列表"""
        return list(self.agent_connections.keys())

    def debug_connections(self):
        """调试连接状态"""
        print(f'🔍 当前WebSocket连接状态:')
        print(f'  - 已连接的Agent数量: {len(self.agent_connections)}')
        print(f'  - Agent连接映射: {list(self.agent_connections.keys())}')
        print(f'  - WebSocket连接数量: {len(self.connection_agents)}')
        for agent_id, ws in self.agent_connections.items():
            print(f'    Agent {agent_id}: {ws.remote_address if hasattr(ws, "remote_address") else "unknown"}')
        return {
            'agent_count': len(self.agent_connections),
            'agent_ids': list(self.agent_connections.keys()),
            'websocket_count': len(self.connection_agents)
        }


# 获取全局WebSocket管理器实例
def get_websocket_manager():
    manager = OfficeWebSocketManager()
    print(f'🔧 获取WebSocket管理器实例: {id(manager)} (server_started={manager.server_started})')
    return manager


class Office_Tool(Base_Tool):
    name = 'Office_Tool'
    description = \
        '''控制前端 Collabora CODE 文档编辑器的工具。
        支持的操作包括：
        - 在当前位置写入内容
        - 查找并读取章节内容
        - 改写章节内容
        - 搜索文字并高亮显示
        - 修改文字格式（字体、颜色等）
        - 查找和操作表格
        '''
    parameters = [
        {
            'name': 'operation',
            'type': 'string',
            'description': \
                '''操作类型，支持以下值：
                - "insert_text": 在当前位置插入文本
                - "find_section": 查找章节内容（未实现）
                - "replace_section": 替换章节内容（未实现）
                - "search_highlight": 搜索并高亮文字（未实现）
                - "format_text": 格式化文字（未实现）
                - "find_table": 查找表格（未实现）
                - "format_table": 格式化表格（未实现）
                ''',
            'required': 'True',
        },
        {
            'name': 'content',
            'type': 'string',
            'description': '要插入或操作的内容文本',
            'required': 'True',
        },
        {
            'name': 'target',
            'type': 'string',
            'description': '操作目标（如章节号、搜索关键词等），某些操作需要',
            'required': 'False',
        },
    ]

    def __init__(self):
        print('🔧 Office_Tool 初始化中...')
        # 使用全局WebSocket管理器
        self.ws_manager = get_websocket_manager()
        print(f'🔧 Office_Tool 获得WebSocket管理器: {id(self.ws_manager)}')
        # 启动WebSocket服务器（如果尚未启动）
        self.ws_manager.start_server()
        print('✅ Office_Tool 初始化完成')

    def call(self, tool_call_paras: Tool_Call_Paras):
        print(f'🔧 Office_Tool 调用参数: {tool_call_paras.callback_tool_paras_dict}')

        # 获取agent_id
        agent_id = tool_call_paras.callback_agent_id
        operation = tool_call_paras.callback_tool_paras_dict.get('operation', 'insert_text')
        content = tool_call_paras.callback_tool_paras_dict.get('content', '')
        target = tool_call_paras.callback_tool_paras_dict.get('target', '')

        print(f'🎯 目标Agent ID: {agent_id}')

        try:
            if operation == 'insert_text':
                result = self._insert_text(agent_id, content)
            else:
                result = f'❌ 操作类型 "{operation}" 暂未实现'

        except Exception as e:
            result = f'❌ Office操作失败: {e!r}'

        # 确保返回安全编码的结果
        safe_result = safe_encode(result)
        action_result = Action_Result(result=safe_result)
        return action_result

    def _insert_text(self, agent_id, text):
        """插入文本到指定Agent的Collabora CODE"""
        command = {
            'type': 'office_operation',
            'operation': 'insert_text',
            'agent_id': agent_id,
            'data': {
                'text': text,
                'timestamp': int(time.time() * 1000)
            }
        }

        # 在新的事件循环中发送命令
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            success, message = loop.run_until_complete(self.ws_manager.send_to_agent(agent_id, command))
            if success:
                return f'✅ 成功向Agent {agent_id} 的Collabora CODE插入文本: "{text[:50]}{"..." if len(text) > 50 else ""}"'
            else:
                # 发送失败时，调试连接状态
                debug_info = self.ws_manager.debug_connections()
                return f'❌ 发送到Agent {agent_id} 失败: {message}\n🔍 调试信息: {debug_info}'
        except Exception as e:
            return f'❌ 插入文本失败: {e!r}'
        finally:
            loop.close()


# 用于测试的主函数
def main_office():
    import config
    from agent.core.tool_agent import Tool_Agent
    from agent.core.agent_config import Agent_Config

    tools = [Office_Tool]
    query = '请在文档中插入一段测试文本："这是通过 Agent 系统插入的测试内容。"'

    config = Agent_Config(
        base_url='http://powerai.cc:28001/v1',  # llama-4-400b
        api_key='empty',
    )

    agent = Tool_Agent(
        query=query,
        tool_classes=tools,
        agent_config=config
    )
    agent.init()
    success = agent.run()


if __name__ == "__main__":
    main_office()