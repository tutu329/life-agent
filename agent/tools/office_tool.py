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

# 全局共享的连接信息，解决单例模式失效问题
_global_agent_connections = {}  # agent_id -> websocket连接的映射
_global_connection_agents = {}  # websocket连接 -> agent_id的反向映射
_global_connection_lock = threading.Lock()
_global_websocket_server = None
_global_server_started = False

# 模块导入检测和强制单例
import sys

_module_import_id = id(_global_agent_connections)
print(f'🔍 office_tool.py 模块导入，全局变量ID: {_module_import_id}')
print(f'🔍 模块路径: {__file__}')
print(f'🔍 模块名称: {__name__}')
print(f'🔍 是否在sys.modules中: {__name__ in sys.modules}')
print(f'🔍 sys.modules中的相关键: {[k for k in sys.modules.keys() if "office" in k.lower()]}')

# 强制模块单例：检查是否已有相同功能的模块被导入
_MODULE_KEY = 'office_websocket_manager_singleton'

# 检查当前模块是否已在sys.modules中
current_module = sys.modules.get(__name__)
if current_module is None:
    print(f'⚠️ 当前模块未在sys.modules中注册，模块名: {__name__}')
    # 强制注册当前模块
    sys.modules[__name__] = sys.modules.get(__name__, type(sys)(__name__))

if _MODULE_KEY in sys.modules:
    # 如果已存在，使用已存在的模块
    existing_module = sys.modules[_MODULE_KEY]
    print(f'🔄 检测到现有Office WebSocket模块，复用现有实例')
    # 复用现有模块的全局变量
    if hasattr(existing_module, '_global_agent_connections'):
        _global_agent_connections = existing_module._global_agent_connections
        _global_connection_agents = existing_module._global_connection_agents
        _global_connection_lock = existing_module._global_connection_lock
        _global_websocket_server = existing_module._global_websocket_server
        _global_server_started = existing_module._global_server_started
        print(f'✅ 成功复用现有模块的全局变量，连接数: {len(_global_agent_connections)}')
    else:
        print(f'⚠️ 现有模块没有全局变量，将使用当前模块实例')
        sys.modules[_MODULE_KEY] = sys.modules[__name__]
else:
    # 注册当前模块为单例
    sys.modules[_MODULE_KEY] = sys.modules[__name__]
    print(f'📝 注册当前模块为Office WebSocket单例')

# 跨模块共享存储 - 使用文件系统解决模块重复导入问题
import os
import fcntl

_shared_connections_file = '/tmp/office_websocket_connections.json'
_shared_connections_lock_file = '/tmp/office_websocket_connections.lock'


def _load_shared_connections():
    """从共享文件加载连接信息"""
    try:
        if os.path.exists(_shared_connections_file):
            with open(_shared_connections_file, 'r') as f:
                data = json.load(f)
                return data.get('agent_connections', {}), data.get('server_started', False)
    except Exception as e:
        print(f'⚠️ 加载共享连接信息失败: {e}')
    return {}, False


def _save_shared_connections(agent_connections_ids, server_started):
    """保存连接信息到共享文件"""
    try:
        # 使用文件锁确保原子性
        with open(_shared_connections_lock_file, 'w') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                data = {
                    'agent_connections': agent_connections_ids,
                    'server_started': server_started,
                    'timestamp': time.time()
                }
                with open(_shared_connections_file, 'w') as f:
                    json.dump(data, f)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        print(f'⚠️ 保存共享连接信息失败: {e}')


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
        global _global_websocket_server, _global_server_started
        self.server = _global_websocket_server
        self.server_thread = None
        # 完全移除实例变量，所有操作直接使用全局变量
        # self.agent_connections 和 self.connection_agents 不再使用
        self.server_started = _global_server_started
        print(f'🔧 OfficeWebSocketManager 初始化 (实例ID={id(self)}, 全局server_started={_global_server_started})')

    def start_server(self):
        """启动WebSocket服务器"""
        global _global_server_started, _global_websocket_server
        print(f'🔍 OfficeWebSocketManager 状态检查: 实例ID={id(self)}, 全局server_started={_global_server_started}')

        if _global_server_started:
            print('⚠️ WebSocket服务器已在全局范围内标记为运行状态，跳过启动')
            self.server_started = _global_server_started
            return

        # 检查端口是否被占用
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('127.0.0.1', 5112))
            if result == 0:
                print('-----------------------------端口5112已被其他进程占用----------------------------------')
                print('🔍 检测到5112端口已被占用，说明WebSocket服务器已在运行')
                print('💡 使用全局状态管理，所有实例将共享连接信息')
                print('🔧 解决方案：标记全局状态为已启动，当前实例将使用共享连接')
                print('----------------------------/端口5112已被其他进程占用----------------------------------')
                _global_server_started = True
                self.server_started = _global_server_started
                print('✅ 已标记全局状态为已启动，当前实例将共享连接信息')
                return

        if self.server_thread is None or not self.server_thread.is_alive():
            print('🚀 启动新的WebSocket服务器线程...')
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            print('🚀 WebSocket服务器启动中... (端口:5112)')
            _global_server_started = True
            self.server_started = _global_server_started
            time.sleep(1)
        else:
            print('⚠️ WebSocket服务器线程已存在且运行中')
            _global_server_started = True
            self.server_started = _global_server_started

    def _run_server(self):
        """运行WebSocket服务器"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def handler(websocket):
            # async def handler(websocket, path):
            print(f'📱 新的WebSocket连接: {websocket.remote_address}')

            try:
                # 持续监听客户端消息，支持重新注册
                print(f'📱 开始监听WebSocket消息: {websocket.remote_address}')
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get('type') == 'register' and data.get('agent_id'):
                            new_agent_id = data['agent_id']

                            # 使用全局锁保护连接操作
                            with _global_connection_lock:
                                # 如果这个WebSocket之前注册过其他agent_id，先清理旧的映射
                                if websocket in _global_connection_agents:
                                    old_agent_id = _global_connection_agents[websocket]
                                    if old_agent_id in _global_agent_connections:
                                        print(f'🗑️ 删除旧Agent连接: {old_agent_id}')
                                        del _global_agent_connections[old_agent_id]
                                        print(f'🔍 删除后agent_connections: {list(_global_agent_connections.keys())}')
                                    print(f'🔄 WebSocket连接从Agent {old_agent_id} 重新注册到 {new_agent_id}')

                                # 注册新的连接
                                print(f'➕ 添加新Agent连接: {new_agent_id}')
                                _global_agent_connections[new_agent_id] = websocket
                                _global_connection_agents[websocket] = new_agent_id
                                print(f'🔍 添加后agent_connections: {list(_global_agent_connections.keys())}')

                                # 同步到共享文件存储
                                _save_shared_connections(list(_global_agent_connections.keys()), True)
                                print(f'✅ Agent {new_agent_id} 已注册WebSocket连接 (已同步到共享存储)')

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

            except websockets.exceptions.ConnectionClosed as e:
                print(f'📱 WebSocket连接已关闭: {websocket.remote_address} - {e}')

            except Exception as e:
                print(f'⚠️ WebSocket连接错误: {websocket.remote_address} - {e}')
                import traceback
                print(f'⚠️ 错误详情: {traceback.format_exc()}')
            finally:
                # 清理连接映射
                with _global_connection_lock:
                    if websocket in _global_connection_agents:
                        agent_id = _global_connection_agents[websocket]
                        print(f'🗑️ 清理断开的Agent连接: {agent_id}')
                        print(f'🔍 清理前agent_connections: {list(_global_agent_connections.keys())}')
                        del _global_agent_connections[agent_id]
                        del _global_connection_agents[websocket]
                        print(f'🔍 清理后agent_connections: {list(_global_agent_connections.keys())}')

                        # 同步到共享文件存储
                        _save_shared_connections(list(_global_agent_connections.keys()), True)
                        print(f'📱 Agent {agent_id} WebSocket连接已断开 (已同步到共享存储)')

        async def start_server():
            global _global_websocket_server
            import ssl
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            try:
                ssl_context.load_cert_chain('/home/tutu/ssl/powerai_public.crt', '/home/tutu/ssl/powerai.key')
                _global_websocket_server = await websockets.serve(handler, '0.0.0.0', 5112, ssl=ssl_context)
                self.server = _global_websocket_server
                print('✅ WebSocket服务器已启动 (WSS端口:5112)')
                await _global_websocket_server.wait_closed()
            except FileNotFoundError:
                print('⚠️ SSL证书未找到，使用普通WebSocket连接')
                _global_websocket_server = await websockets.serve(handler, '0.0.0.0', 5112)
                self.server = _global_websocket_server
                print('✅ WebSocket服务器已启动 (WS端口:5112)')
                await _global_websocket_server.wait_closed()
            except Exception as e:
                print(f'❌ SSL WebSocket启动失败: {e}，回退到普通连接')
                try:
                    _global_websocket_server = await websockets.serve(handler, '0.0.0.0', 5112)
                    self.server = _global_websocket_server
                    print('✅ WebSocket服务器已启动 (WS端口:5112)')
                    await _global_websocket_server.wait_closed()
                except Exception as fallback_error:
                    print(f'❌ WebSocket服务器启动完全失败: {fallback_error}')

        loop.run_until_complete(start_server())

    async def send_to_agent(self, agent_id, command):
        """向指定agent发送命令"""
        with _global_connection_lock:
            # 先尝试从共享文件加载连接信息
            shared_agent_ids, shared_server_started = _load_shared_connections()

            if agent_id not in _global_agent_connections:
                # 检查共享存储中是否有该连接
                if agent_id in shared_agent_ids:
                    print(f'🔍 在共享存储中找到Agent {agent_id}，但当前模块实例没有WebSocket对象')
                    print(f'💡 尝试使用现有连接代理发送消息...')
                    return await self._try_proxy_send(agent_id, command)

                # 检查是否有其他可用连接进行代理
                if len(_global_agent_connections) > 0:
                    print(f'🔄 Agent {agent_id} 不在当前连接中，尝试使用现有连接代理发送')
                    print(f'🔍 当前可用连接: {list(_global_agent_connections.keys())}')
                    return await self._try_proxy_send(agent_id, command)

                # 全局和共享存储都没有该agent的连接信息
                print(f'⚠️ Agent {agent_id} 不在连接列表中 (实例ID={id(self)}, 模块ID={_module_import_id})')
                print(f'🔍 当前模块连接: {list(_global_agent_connections.keys())}')
                print(f'🔍 共享存储连接: {shared_agent_ids}')
                if len(_global_agent_connections) == 0 and len(shared_agent_ids) == 0:
                    return False, f'Agent {agent_id} 没有WebSocket连接 (全局和共享存储都无连接)'
                else:
                    return False, f'Agent {agent_id} 没有WebSocket连接 (模块连接: {list(_global_agent_connections.keys())}, 共享连接: {shared_agent_ids})'

            websocket = _global_agent_connections[agent_id]
        try:
            command_json = json.dumps(command, ensure_ascii=False)
            await websocket.send(command_json)
            return True, 'success'
        except Exception as e:
            # 连接可能已断开，清理映射
            print(f'🗑️ 发送失败，清理Agent连接: {agent_id}')
            with _global_connection_lock:
                print(f'🔍 清理前agent_connections: {list(_global_agent_connections.keys())}')
                if websocket in _global_connection_agents:
                    del _global_connection_agents[websocket]
                if agent_id in _global_agent_connections:
                    del _global_agent_connections[agent_id]
                print(f'🔍 清理后agent_connections: {list(_global_agent_connections.keys())}')
            return False, f'发送失败: {e}'

    async def _try_proxy_send(self, target_agent_id, command):
        """尝试通过现有连接代理发送消息"""
        print(f'🔧 开始代理发送：目标={target_agent_id}')

        with _global_connection_lock:
            print(f'🔍 当前_global_agent_connections数量: {len(_global_agent_connections)}')
            print(f'🔍 可用连接: {list(_global_agent_connections.keys())}')

            if len(_global_agent_connections) == 0:
                print(f'❌ 没有可用的WebSocket连接进行代理')
                return False, '没有可用的WebSocket连接进行代理'

            # 使用任何一个可用连接发送消息
            for available_agent_id, websocket in _global_agent_connections.items():
                try:
                    print(f'🔄 尝试通过Agent {available_agent_id} 代理发送给Agent {target_agent_id}')

                    # 修改命令，添加代理信息但保持原始结构
                    proxy_command = command.copy()
                    proxy_command['proxy_mode'] = True
                    proxy_command['original_target_agent'] = target_agent_id
                    proxy_command['proxy_agent'] = available_agent_id

                    print(f'🔧 准备发送代理命令: operation={proxy_command.get("operation", "unknown")}')

                    command_json = json.dumps(proxy_command, ensure_ascii=False)
                    print(f'🔧 开始发送WebSocket消息...')
                    await websocket.send(command_json)
                    print(f'✅ WebSocket发送完成')
                    return True, f'通过Agent {available_agent_id} 代理发送成功'

                except Exception as e:
                    print(f'⚠️ 通过Agent {available_agent_id} 代理发送失败: {e}')
                    import traceback
                    print(f'⚠️ 错误详情: {traceback.format_exc()}')
                    continue

            print(f'❌ 所有可用连接的代理发送都失败了')
            return False, '所有代理连接都失败'

    def get_connected_agents(self):
        """获取已连接的agent列表"""
        with _global_connection_lock:
            return list(_global_agent_connections.keys())

    def debug_connections(self):
        """调试连接状态"""
        import traceback
        with _global_connection_lock:
            # 加载共享存储信息
            shared_agent_ids, shared_server_started = _load_shared_connections()

            print(f'🔍 WebSocket连接状态诊断 (实例ID={id(self)}, 模块ID={_module_import_id}):')
            print(f'  📍 当前模块连接:')
            print(f'    - Agent数量: {len(_global_agent_connections)}')
            print(f'    - Agent列表: {list(_global_agent_connections.keys())}')
            print(f'    - WebSocket数量: {len(_global_connection_agents)}')

            print(f'  📁 共享存储连接:')
            print(f'    - Agent数量: {len(shared_agent_ids)}')
            print(f'    - Agent列表: {shared_agent_ids}')
            print(f'    - 服务器状态: {shared_server_started}')

            print(f'  🔗 详细连接信息:')
            for agent_id, ws in _global_agent_connections.items():
                try:
                    ws_state = ws.state if hasattr(ws, 'state') else 'unknown'
                    ws_addr = ws.remote_address if hasattr(ws, 'remote_address') else 'unknown'
                    print(f'    Agent {agent_id}: {ws_addr} (state: {ws_state})')
                except Exception as e:
                    print(f'    Agent {agent_id}: 连接状态检查失败 - {e}')

            # 检测模块重复导入问题
            if len(shared_agent_ids) > 0 and len(_global_agent_connections) == 0:
                print(f'  ⚠️ 检测到模块重复导入问题：共享存储有连接，但当前模块实例无连接')

            # 打印调用栈，帮助定位是谁调用了debug_connections
            print(f'🔍 调用栈:')
            for line in traceback.format_stack()[-3:-1]:  # 显示最近的2层调用
                print(f'    {line.strip()}')

            return {
                'agent_count': len(_global_agent_connections),
                'agent_ids': list(_global_agent_connections.keys()),
                'websocket_count': len(_global_connection_agents)
            }


# 跨模块实例缓存 - 终极解决方案
_global_manager_instance = None


# 获取全局WebSocket管理器实例 - 支持跨模块单例
def get_websocket_manager():
    global _global_manager_instance

    # 检查是否有已注册的单例模块
    if _MODULE_KEY in sys.modules:
        existing_module = sys.modules[_MODULE_KEY]
        if hasattr(existing_module, 'OfficeWebSocketManager'):
            # 如果存在，从已注册模块获取实例
            if hasattr(existing_module.OfficeWebSocketManager,
                       '_instance') and existing_module.OfficeWebSocketManager._instance:
                manager = existing_module.OfficeWebSocketManager._instance
                print(f'🔧 复用已存在的WebSocket管理器实例: {id(manager)} (server_started={manager.server_started})')
                _global_manager_instance = manager  # 缓存到当前模块
                return manager

    # 检查当前模块的缓存
    if _global_manager_instance is not None:
        print(f'🔧 使用当前模块缓存的管理器实例: {id(_global_manager_instance)}')
        return _global_manager_instance

    # 否则创建新实例
    manager = OfficeWebSocketManager()
    _global_manager_instance = manager  # 缓存新实例
    print(f'🔧 创建新的WebSocket管理器实例: {id(manager)} (server_started={manager.server_started})')
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
        # 检查初始化时的连接状态
        self.ws_manager.debug_connections()

    def call(self, tool_call_paras: Tool_Call_Paras):
        print(f'🔧 Office_Tool 调用参数: {tool_call_paras.callback_tool_paras_dict}')

        # 获取顶层agent_id（用于WebSocket连接管理）
        top_agent_id = tool_call_paras.callback_top_agent_id
        current_agent_id = tool_call_paras.callback_agent_id
        operation = tool_call_paras.callback_tool_paras_dict.get('operation', 'insert_text')
        content = tool_call_paras.callback_tool_paras_dict.get('content', '')
        target = tool_call_paras.callback_tool_paras_dict.get('target', '')

        print(f'🎯 当前Agent ID: {current_agent_id}')
        print(f'🔝 顶层Agent ID: {top_agent_id}')

        # 在执行操作前检查连接状态
        print('🔍 执行Office操作前的连接状态:')
        self.ws_manager.debug_connections()

        try:
            print(f'🔍 执行Office操作: {operation}，目标Agent: {top_agent_id}')
            if operation == 'insert_text':
                result = self._insert_text(top_agent_id, content, current_agent_id)
            else:
                result = f'❌ 操作类型 "{operation}" 暂未实现'

        except Exception as e:
            result = f'❌ Office操作失败: {e!r}'

        # 确保返回安全编码的结果
        safe_result = safe_encode(result)
        action_result = Action_Result(result=safe_result)
        return action_result

    def _insert_text(self, top_agent_id, text, current_agent_id=None):
        """插入文本到指定顶层Agent的Collabora CODE"""
        command = {
            'type': 'office_operation',
            'operation': 'insert_text',
            'agent_id': top_agent_id,
            'current_agent_id': current_agent_id,  # 添加当前执行的Agent ID信息
            'data': {
                'text': text,
                'timestamp': int(time.time() * 1000)
            }
        }

        # 在新的事件循环中发送命令
        print(f'🔧 准备创建新的事件循环发送命令...')
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            print(f'🔧 开始异步发送到Agent: {top_agent_id}')
            success, message = loop.run_until_complete(self.ws_manager.send_to_agent(top_agent_id, command))
            print(f'🔧 异步发送结果: success={success}, message={message}')

            if success:
                agent_info = f"顶层Agent {top_agent_id}"
                if current_agent_id and current_agent_id != top_agent_id:
                    agent_info += f" (通过子Agent {current_agent_id})"
                return f'✅ 成功向{agent_info}的Collabora CODE插入文本: "{text[:50]}{"..." if len(text) > 50 else ""}"'
            else:
                # 发送失败时，调试连接状态
                debug_info = self.ws_manager.debug_connections()
                return f'❌ 发送到顶层Agent {top_agent_id} 失败: {message}\n🔍 调试信息: {debug_info}'
        except Exception as e:
            print(f'❌ 异步发送过程中出现异常: {e!r}')
            import traceback
            print(f'❌ 异常详情: {traceback.format_exc()}')
            return f'❌ 插入文本失败: {e!r}'
        finally:
            print(f'🔧 关闭事件循环')
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