import json

from agent.base_tool import Base_Tool

class Database_Tool(Base_Tool):
    name='Database_Tool'
    description=\
'''通过表名和字段名，获取数据库中对应数据，并将数据存放于全局共享变量g_agent_share_data_dict["some_agent_id"]["some_var_name"]中。
'''
    parameters=[
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
             callback_agent_id
             ):
        print(f'tool_paras_dict: "{callback_tool_paras_dict}"')
        table_name = callback_tool_paras_dict['table_name']
        field_names = json.loads(callback_tool_paras_dict['field_names'])

        # 调用工具
        print(f'工具"Database_Tool"已被调用，table_name:{table_name!r}, field_names:{field_names!r}')
        share_data_name = 'shared_database_data'
        rtn_str = f'工具"Database_Tool"调用成功，数据已成功存入全局共享变量g_agent_share_data_dict[{callback_agent_id}][{share_data_name}]'

        # 调用工具后，结果作为action_result返回
        action_result = rtn_str
        return action_result

def main_db_tool():
    import config
    from agent.tool_agent import Tool_Agent
    from agent.agent_config import Config

    tools=[Database_Tool]
    print(f'os: "{config.get_os()}"')
    if config.get_os()=='windows':
        query = r'请分析下这两年杭州规上行业的用电量异动情况，要聚焦到关键用户'
    else:
        pass

    config = Config(
        base_url='http://powerai.cc:28001/v1',   #qwen3-235b
        base_url='http://powerai.cc:28002/v1',   #qwq
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