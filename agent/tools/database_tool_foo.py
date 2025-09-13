import json5

from agent.tools.base_tool import Base_Tool
from agent.tools.protocol import Data_Set_Info, Action_Result
# from agent.core.legacy_protocol import Data_Set_Info, Action_Result

# from agent.base_tool import Data_Attached_Tool

class Database_Tool(Base_Tool):
    tool_name= 'Database_Tool'
    tool_description=\
'''本工具，通过表名和字段名，获取数据库中对应数据，并将数据通过push_to_frontend("some_agent_id", "some_var_name")传给前端中。
'''
    tool_parameters=[
        {
            'name': 'table_name',
            'type': 'string',
            'description': \
'''
本参数为数据库的表名
''',
            'required': 'True',
        },
        {
            'name': 'field_names',
            'type': 'string',
            'description': \
'''
本参数为数据库的字段名列表字符串，如"['field1','field2', ...]"
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
        print(f'tool_paras_dict: {callback_tool_paras_dict!r}')
        print(f'type of callback_tool_paras_dict: {type(callback_tool_paras_dict)!r}')
        if isinstance(callback_tool_paras_dict, dict):
            table_name = callback_tool_paras_dict['table_name']
            field_names = callback_tool_paras_dict['field_names']
            print(f'field_names: {field_names!r}')
            field_names = json5.loads(callback_tool_paras_dict['field_names'])

            # 调用工具
            # print(f'工具"Database_Tool"已被调用，table_name:{table_name!r}, field_names:{field_names!r}')
            share_data_name = 'shared_database_data'
            rtn_str = f'工具"Database_Tool"已调用，数据已通过push_to_frontend({callback_agent_id}, {share_data_name})发给了前端，当然任务还未最终完成。'
            # print(rtn_str)


            data_set_info = Data_Set_Info(
                data_set_content_url=None,
                schema=None,
                rows=30,
                cols=20,
                sample=[
                    {'name':'tutu', 'kWh':5200},
                    {'name':'mumu', 'kWh':8800},
                ],
                expires_at=None
            )

            action_result = Action_Result(result=rtn_str, data_set_info=data_set_info)
            # updated_tool_ctx = update_tool_context_info(callback_tool_ctx, action_result=rtn_str, data_set_info=data_set_info)
            return action_result
        else:
            # 返回的不是数据dict，而是string，表明发生了error
            return '返回的不是数据dict，而是string，表明发生了error'

def main_db_tool():
    import config
    from agent.core.react_agent import Tool_Agent
    from agent.tools.frontend_chart_code_transfer_foo import Frontend_Chart_Code_Transfer_Tool
    from agent.core.agent_config import Agent_Config

    tools=[Database_Tool, Frontend_Chart_Code_Transfer_Tool]
    print(f'os: "{config.get_os()}"')

    if config.get_os()=='windows':
        # query = r'请以图文的方式分析下这两年杭州规上行业的用电量异动情况，要聚焦到关键用户。先推送数据到数据，再写前端代码发给前端，然后等待前端渲染反馈。表名是hangzhou_elec_2024，字段名有date、electricity、gdp、sector、customer_name'
        query = r'请以图文的方式分析下这两年杭州规上行业的用电量异动情况，要聚焦到关键用户。表名是hangzhou_elec_2024，字段名有date、electricity、gdp、sector、customer_name'
    else:
        # query = r'请以图文的方式分析下这两年杭州规上行业的用电量异动情况，要聚焦到关键用户。先推送数据到数据，再写前端代码发给前端，然后等待前端渲染反馈。表名是hangzhou_elec_2024，字段名有date、electricity、gdp、sector、customer_name'
        query = r'请以图文的方式分析下这两年杭州规上行业的用电量异动情况，要聚焦到关键用户。表名是hangzhou_elec_2024，字段名有date、electricity、gdp、sector、customer_name'

    config = Agent_Config(
        # base_url='http://powerai.cc:28001/v1',   # qwen3-235b
        base_url='http://powerai.cc:28001/v1',   # deepseek-r1-671b
        # base_url='http://powerai.cc:28002/v1',   # qwq
        api_key='empty',
    )
    agent = Tool_Agent(
        query=query,
        tool_classes=tools,
        agent_config=config
    )
    agent.init()
    success = agent.run()
    print(f'agent执行完毕，最终回复是: \n"{agent.get_final_answer()}"')

if __name__ == "__main__":
    main_db_tool()