import json

from agent.base_tool import Base_Tool

class Frontend_Chart_Code_Transfer_Tool(Base_Tool):
    name='Frontend_Chart_Code_Transfer_Tool'
    description=\
'''将已生成的前端chart代码发送给前端，并在前端动态执行。
'''
    parameters = [
        {
            'name': 'frontend_chart_code',
            'type': 'string',
            'description': \
'''
本参数为需要传给前端的chart代码
''',
            'required': 'True',
        },
        {
            'name': 'field_names_used_to_draw_chart_by_frontend',
            'type': 'string',
            'description': \
'''
本参数为需要告诉前端的用于绘制chart的数据的字段名列表字符串，如"['field1','field2', ...]"
''',
            'required': 'True',
        },
    ]
    def __init__(self):
        pass

    def call(self,
             callback_tool_paras_dict,
             callback_agent_config,
             callback_agent_id
             ):
        print(f'tool_paras_dict: "{callback_tool_paras_dict}"')
        frontend_chart_code = callback_tool_paras_dict['frontend_chart_code']

        # 调用工具
        print(f'工具"Frontend_Chart_Code_Transfer_Tool"已被调用，agent_id:{callback_agent_id!r}')
        share_data_name = 'shared_database_data'
        rtn_str = f'工具"Frontend_Chart_Code_Generate_Tool"调用成功，代码已被传给前端，并已成功执行。\n代码为："\n{frontend_chart_code}"'

        # 调用工具后，结果作为action_result返回
        action_result = rtn_str
        return action_result

def main_db_tool():
    import config
    from agent.tool_agent import Tool_Agent
    from agent.agent_config import Config

    tools=[Frontend_Chart_Code_Transfer_Tool]
    print(f'os: "{config.get_os()}"')
    if config.get_os()=='windows':
        query = r'请将代码"print("hello world")"传给前端'
    else:
        pass

    config = Config(
        base_url='http://powerai.cc:28001/v1',   #qwen3-235b
        # base_url='http://powerai.cc:28002/v1',   #qwq
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
    main_db_tool()