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
        self.websocket_url = 'wss://powerai.cc:5112'  # WebSocket 服务器地址
        self.connected_clients = set()  # 连接的客户端
        self.server = None
        self.server_thread = None
        self.start_websocket_server()

    def start_websocket_server(self):
        """启动 WebSocket 服务器"""
        if self.server_thread is None or not self.server_thread.is_alive():
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            print(f'🚀 WebSocket服务器启动中... (端口:5112)')
            time.sleep(1)  # 等待服务器启动

    def _run_server(self):
        """运行 WebSocket 服务器的线程函数"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def handler(websocket):
        # async def handler(websocket, path):
            print(f'📱 新的WebSocket连接: {websocket.remote_address}')
            self.connected_clients.add(websocket)
            try:
                await websocket.wait_closed()
            except Exception as e:
                print(f'⚠️ WebSocket连接错误: {e}')
            finally:
                self.connected_clients.discard(websocket)
                print(f'📱 WebSocket连接已断开: {websocket.remote_address}')

        async def start_server():
            # 使用 SSL 证书（根据用户说明，必须使用 HTTPS/WSS）
            import ssl
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            try:
                # 使用 powerai.cc 的证书
                ssl_context.load_cert_chain('/home/tutu/ssl/powerai_public.crt', '/home/tutu/ssl/powerai.key')

                self.server = await websockets.serve(
                    handler,
                    'localhost',
                    5112,
                    ssl=ssl_context
                )
                print('✅ WebSocket服务器已启动 (WSS端口:5112)')
                await self.server.wait_closed()
            except FileNotFoundError:
                # 如果没有证书文件，使用普通连接
                print('⚠️ SSL证书未找到，使用普通WebSocket连接')
                self.server = await websockets.serve(handler, 'localhost', 5112)
                print('✅ WebSocket服务器已启动 (WS端口:5112)')
                await self.server.wait_closed()
            except Exception as e:
                print(f'❌ WebSocket服务器启动失败: {e}')

        loop.run_until_complete(start_server())

    async def send_command_to_clients(self, command):
        """向所有连接的客户端发送命令"""
        if not self.connected_clients:
            print('⚠️ 没有连接的WebSocket客户端')
            return False

        command_json = json.dumps(command, ensure_ascii=False)
        print(f'📤 发送命令到 {len(self.connected_clients)} 个客户端: {command_json}')

        disconnected_clients = set()
        for client in self.connected_clients:
            try:
                await client.send(command_json)
            except Exception as e:
                print(f'❌ 发送到客户端失败: {e}')
                disconnected_clients.add(client)

        # 清理断开的连接
        self.connected_clients -= disconnected_clients
        return len(self.connected_clients) > 0

    def call(self, tool_call_paras: Tool_Call_Paras):
        print(f'🔧 Office_Tool 调用参数: {tool_call_paras.callback_tool_paras_dict}')

        operation = tool_call_paras.callback_tool_paras_dict.get('operation', 'insert_text')
        content = tool_call_paras.callback_tool_paras_dict.get('content', '')
        target = tool_call_paras.callback_tool_paras_dict.get('target', '')

        try:
            if operation == 'insert_text':
                result = self._insert_text(content)
            else:
                result = f'❌ 操作类型 "{operation}" 暂未实现'

        except Exception as e:
            result = f'❌ Office操作失败: {e!r}'

        # 确保返回安全编码的结果
        safe_result = safe_encode(result)
        action_result = Action_Result(result=safe_result)
        return action_result

    def _insert_text(self, text):
        """插入文本到 Collabora CODE"""
        command = {
            'type': 'office_operation',
            'operation': 'insert_text',
            'data': {
                'text': text,
                'timestamp': int(time.time() * 1000)
            }
        }

        # 在新的事件循环中发送命令
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            success = loop.run_until_complete(self.send_command_to_clients(command))
            if success:
                return f'✅ 成功向 Collabora CODE 插入文本: "{text[:50]}{"..." if len(text) > 50 else ""}"'
            else:
                return '⚠️ 没有连接的前端客户端，无法插入文本'
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