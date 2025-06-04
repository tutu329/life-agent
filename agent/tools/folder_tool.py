
# 如果报错：Failed to parse the request body as JSON: messages[1].content: lone leading surrogate in hex escape at line 1 column 10594
# 或者报错：'utf-8' codec can't encode characters in position 3186-3199: surrogates not allowed
# 原因是出现了这种名字的文件：110kV��������������ͼ.jpg
# 这时要用utils/encode.py的safe_encode()才行

from utils.encode import safe_encode
from agent.tools.base_tool import Base_Tool
from agent.tools.protocol import Action_Result, Tool_Call_Paras
# from agent.core.legacy_protocol import Action_Result
from utils.folder import get_folder_all_items_string

class Folder_Tool(Base_Tool):
    name='Folder_Tool'
    description=\
'''返回指定文件夹下所有文件和文件夹的名字信息。
'''
    parameters=[
        {
            'name': 'dir',
            'type': 'string',
            'description': \
'''
本参数为文件夹所在的路径
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
    #          callback_father_agent_exp,
    #          ):
        print(f'tool_paras_dict: "{tool_call_paras.callback_tool_paras_dict}"')
        dir = tool_call_paras.callback_tool_paras_dict['dir']

        try:
            # 调用工具
            # files_str = get_folder_files_info_string(directory=dir, mode='name')
            items_str = safe_encode(get_folder_all_items_string(directory=dir))
            # files_str = get_folder_files_info_string(directory=dir, mode='basename')
        except Exception as e:
            items_str = f'报错: {e!r}'

        # 调用工具后，结果作为action_result返回
        action_result = Action_Result(result=items_str)
        # action_result = items_str
        return action_result

def main_folder():
    import config
    from agent.core.tool_agent import Tool_Agent
    from agent.tools.folder_tool import Folder_Tool
    from agent.core.agent_config import Agent_Config

    tools=[Folder_Tool]
    print(f'os: "{config.get_os()}"')
    if config.get_os()=='windows':
        # query = r'请告诉我"file_to_find.txt"在"d:\demo\"文件夹的哪个具体文件夹中'
        query = r'请告诉我"file_to_find.txt"在"y:\demo\"文件夹的哪个具体文件夹中'
    else:
        query = r'请告诉我"./"文件夹里有哪些文件，不作任何解释，直接输出结果'

    config = Agent_Config(
        # base_url='http://powerai.cc:8001/v1',   #qwen3-30b
        # base_url='http://powerai.cc:28002/v1',   #qwq
        base_url='http://powerai.cc:28001/v1',  # llama-4-400b#llama-4-400b
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

if __name__ == "__main__":
    main_folder()