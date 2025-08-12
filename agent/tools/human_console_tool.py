from agent.tools.base_tool import Base_Tool
from agent.tools.protocol import Action_Result, Tool_Call_Paras
# from agent.core.legacy_protocol import Action_Result

class Human_Console_Tool(Base_Tool):
    tool_name= 'Human_Console_Tool'
    tool_description=\
'''本工具用于向用户获取反馈信息(当你不清楚用户问题是否完全解决时，就要通过本工具向用户询问，而不是通过直接输出询问用户)。
'''
    tool_parameters=[
        {
            'name': 'question',
            'type': 'string',
            'description': \
'''
本参数为向用户的提问
''',
            'required': 'True',
        },
    ]
    def __init__(self):
        pass

    def call(self, tool_call_paras:Tool_Call_Paras):
    # def call(self,
    #          callback_tool_paras_dict,
    #          callback_agent_config,
    #          callback_agent_id,
    #          callback_last_tool_ctx,
    #          callback_father_agent_exp
    #          ):
        print(f'tool_paras_dict: "{tool_call_paras.callback_tool_paras_dict}"')
        question = tool_call_paras.callback_tool_paras_dict['question']

        # 调用工具
        res = input(f'Agent: {question}')

        # 调用工具后，结果作为action_result返回
        action_result = Action_Result(result=res)
        return action_result

def main_agent_as_tool():
    from agent.core.tool_agent import Tool_Agent
    from agent.core.agent_config import Agent_Config
    from agent.tools.folder_tool import Folder_Tool

    tools1=[Human_Console_Tool, Folder_Tool]
    query = r'请告诉我当前文件夹下有哪些文件'
    # query = r'请告诉我"file_to_find.txt"在"d:\demo\"文件夹的哪个具体文件夹中'
    # query = r'请告诉我"file_to_find.txt"在"y:\demo\"文件夹的哪个具体文件夹中'
    config = Agent_Config(
        # base_url='http://powerai.cc:28001/v1',  # llama-4-400b#llama-4-400b
        # base_url='http://powerai.cc:28002/v1',  # qwen3-235b
        base_url='https://api.deepseek.com/v1',
        # base_url='http://powerai.cc:38001/v1',   #deepseek-r1-671b
        # base_url='http://powerai.cc:8001/v1',   #qwen3-30b
        # api_key='empty',
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        # model_id='deepseek-reasoner',  # 模型指向 DeepSeek-R1-0528
        llm_model_id='deepseek-chat',     # 模型指向 DeepSeek-V3-0324
    )

    folder_agent_as_tool = Tool_Agent(
        tool_classes=tools1,
        agent_config=config,
        as_tool_name='Folder_Agent_As_Tool',
        as_tool_description='本工具用于获取文件夹中的文件和文件夹信息',
    ).init()

    tools2=[Human_Console_Tool, folder_agent_as_tool]

    agent = Tool_Agent(
        tool_classes=tools2,
        agent_config=config,
        has_history=True,
        tool_agent_experience_json_path='my_1st_example_of_agent_as_tool.json',
    )
    agent.init()
    success = agent.run(query=query)
    print(f'\nagent最终答复: \n"{agent.get_final_answer()}"')
    success = agent.run(query=r'再告诉我一下当前文件夹下有哪些文件，忘记了')
    # success = agent.run(query=r'再告诉我一下"file_to_find.txt"在"d:\demo\"文件夹的哪个具体文件夹中，忘记了')
    print(f'\nagent最终答复: \n"{agent.get_final_answer()}"')

def main_human_console_tool():
    import config
    from agent.core.tool_agent import Tool_Agent
    from agent.core.agent_config import Agent_Config
    from agent.tools.folder_tool import Folder_Tool

    tools=[Human_Console_Tool, Folder_Tool]
    print(f'os: "{config.get_os()}"')
    if config.get_os()=='windows':
        query = r'请告诉我"file_to_find.txt"在"d:\demo\"文件夹的哪个具体文件夹中'
        # query = r'请告诉我"file_to_find.txt"在"y:\demo\"文件夹的哪个具体文件夹中，搜索过程中如有疑问，要向用户问清楚'
    else:
        # query = r'请告诉我"file_to_find.txt"在"d:\demo\"文件夹的哪个具体文件夹中'
        query = r'请告诉我"file_to_find.txt"在"y:\demo\"文件夹的哪个具体文件夹中'

    config = Agent_Config(
        # base_url='http://powerai.cc:8001/v1',   #qwen3-30b
        # base_url='http://powerai.cc:28002/v1',   #qwq
        base_url='http://powerai.cc:28001/v1',  # llama-4-400b or qwen3-235b
        # base_url='http://powerai.cc:38001/v1',   #deepseek-r1-671b
        api_key='empty',
    )

    agent = Tool_Agent(
        query=query,
        tool_classes=tools,
        agent_config=config
    )
    agent.init()
    success = agent.run()
    print(f'\nagent最终答复: \n"{agent.get_final_answer()}"')

if __name__ == "__main__":
    main_agent_as_tool()
    # main_human_console_tool()