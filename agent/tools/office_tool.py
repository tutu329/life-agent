import time
from utils.encode import safe_encode
from agent.tools.base_tool import Base_Tool
from agent.tools.protocol import Action_Result, Tool_Call_Paras

from utils.web_socket_manager import get_websocket_manager

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
        # 使用通用WebSocket管理器
        self.ws_manager = get_websocket_manager()
        # 启动WebSocket服务器（如果尚未启动）
        self.ws_manager.start_server()
        print('✅ Office_Tool 初始化完成')

    def call(self, tool_call_paras: Tool_Call_Paras):
        print(f'🔧 Office_Tool 调用参数: {tool_call_paras.callback_tool_paras_dict}')

        # 获取顶层agent_id（用于WebSocket连接管理）
        top_agent_id = tool_call_paras.callback_top_agent_id
        operation = tool_call_paras.callback_tool_paras_dict.get('operation', 'insert_text')
        content = tool_call_paras.callback_tool_paras_dict.get('content', '')
        target = tool_call_paras.callback_tool_paras_dict.get('target', '')

        print(f'🎯 目标Agent ID: {top_agent_id}')

        try:
            if operation == 'insert_text':
                # 构建Office操作命令
                command = {
                    'type': 'office_operation',
                    'operation': 'insert_text',
                    'agent_id': top_agent_id,
                    'data': {
                        'text': content,
                        'timestamp': int(time.time() * 1000)
                    }
                }

                # 发送命令到WebSocket客户端
                success, message = self.ws_manager.send_command(top_agent_id, command)
                if success:
                    result = f'✅ 成功向客户端 {top_agent_id} 插入文本: "{content[:50]}{"..." if len(content) > 50 else ""}"'
                else:
                    result = f'❌ 向客户端 {top_agent_id} 插入文本失败: {message}'
            else:
                result = f'❌ 操作类型 "{operation}" 暂未实现'

        except Exception as e:
            result = f'❌ Office操作失败: {e!r}'

        # 确保返回安全编码的结果
        safe_result = safe_encode(result)
        action_result = Action_Result(result=safe_result)
        return action_result


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