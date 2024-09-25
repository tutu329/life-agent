from agent.tool_agent_prompts import Base_Tool
from utils.extract import extract_dict_string
from utils.folder import get_folder_files_info_string
import json5

class Folder_Tool(Base_Tool):
    name='folder_tool'
    description=\
'''返回指定文件夹下所有文件的文件名信息。
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

    def call(self, in_thoughts):
        dict_string = extract_dict_string(in_thoughts)
        dict = json5.loads(dict_string)
        dir = dict['tool_parameters']['dir']

        # 调用工具
        files_str = get_folder_files_info_string(directory=dir, mode='basename')

        # 调用工具后，结果作为action_result返回
        action_result = files_str
        return action_result