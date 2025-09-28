from agent.tools.base_tool import Base_Tool
from agent.tools.legacy_protocol import Action_Result
# from agent.core.legacy_protocol import Action_Result

class Frontend_Chart_Code_Transfer_Tool(Base_Tool):
    tool_name= 'Frontend_Chart_Code_Transfer_Tool'
    tool_description = \
'''本工具将代码传给前端，系统在前端用javascript完成渲染，本工具不会直接给出最终结果。本工具的具体要求包括，
1)输入：通过参数frontend_chart_code输入javascript程序，程序必须从新的一行顶格开始，编写程序时要一步一步想清楚。
'''
    tool_parameters = [
        {
            'name': 'frontend_chart_code',
            'type': 'string',
            'description': \
'''
1）本参数为输入的javascript代码字符串，必须以"对囊括起来，绝对不能用```或\'\'\'或\"\"\"括起来。
2）javascript代码字符串内部的引号必须根据嵌套情况用\"对或\'对。
3）javascript代码字符串内容的回车必须用\\\\n。
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
             callback_agent_id,
             callback_last_tool_ctx
             ):
        print(f'tool_paras_dict: "{callback_tool_paras_dict}"')
        frontend_chart_code = callback_tool_paras_dict['frontend_chart_code']

        # 调用工具
        print(f'工具"Frontend_Chart_Code_Transfer_Tool"已被调用，agent_id:{callback_agent_id!r}')
        share_data_name = 'shared_database_data'
        rtn_str = f'工具"Frontend_Chart_Code_Generate_Tool"调用成功，代码已被传给前端，并已成功执行。\n代码为："\n{frontend_chart_code}"'

        # updated_tool_ctx = update_tool_context_info(callback_tool_ctx, action_result=rtn_str, data_set_info=None)
        # 调用工具后，结果作为action_result返回
        # action_result = rtn_str
        action_result = Action_Result(result=rtn_str)

        if callback_last_tool_ctx is not None:
            print(f'==============Frontend_Chart_Code_Transfer_Tool.callback_last_tool_ctx.data_set_info===============\n{callback_last_tool_ctx.data_set_info}')
        else:
            print('----------------wrong: callback_last_tool_ctx is None!---------------------')
        return action_result

def main_db_tool():
    import config
    from agent.core.react_agent import Tool_Agent
    from agent.core.agent_config import Agent_Config

    tools=[Frontend_Chart_Code_Transfer_Tool]
    print(f'os: "{config.get_os()}"')
    if config.get_os()=='windows':
        query = r'请将代码"print("hello world")"传给前端'
    else:
        pass

    config = Agent_Config(
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