from agent.base_tool import Base_Tool
from utils.extract import extract_dict_string
from utils.folder import get_folder_files_info_string, get_folder_all_items_string
import json5

from config import dred, dgreen, dblue, dcyan, dyellow

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

    def call(self,
             in_thoughts,
             in_is_web_server=True,
             in_client_data_sse_stream_buf=None,
             ):
        # dred('-----------------Folder_Tool.call() invoked.---------------------')
        dict_string = extract_dict_string(in_thoughts)
        dict = json5.loads(dict_string)
        dir = dict['tool_parameters']['dir']

        # 调用工具
        # files_str = get_folder_files_info_string(directory=dir, mode='name')
        items_str = get_folder_all_items_string(directory=dir)
        # files_str = get_folder_files_info_string(directory=dir, mode='basename')

        # 调用工具后，结果作为action_result返回
        action_result = items_str
        # dred('-----------------Folder_Tool.call() result:---------------------')
        # dred(action_result)
        return action_result

def main_folder():
    import config
    from agent.tool_agent import Tool_Agent
    from agent.tools.folder_tool import Folder_Tool
    tools=[Folder_Tool]
    print(f'os: "{config.get_os()}"')
    if config.get_os()=='windows':
        # query = r'请告诉我"file_to_find.txt"在"d:\demo\"文件夹的哪个具体文件夹中'
        query = r'请告诉我"file_to_find.txt"在"y:\demo\"文件夹的哪个具体文件夹中'
    else:
        query = r'请告诉我"./"文件夹里有哪些文件，不作任何解释，直接输出结果'
    agent = Tool_Agent(
        query=query,
        tool_classes=tools,
        stream_result=dyellow,
        in_output_stream_to_console=True,
        in_base_url='http://powerai.cc:28001/v1', #llama-4-400b#llama-4-400b
        # in_base_url='http://powerai.cc:38001/v1',   #deepseek-r1-671b
        in_api_key='empty',
    )
    agent.init()
    success = agent.run()

if __name__ == "__main__":
    main_folder()