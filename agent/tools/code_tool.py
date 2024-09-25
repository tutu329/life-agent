from agent.base_tool import Base_Tool
from utils.extract import extract_dict_string, extract_code
import json5

from config import dred, dgreen, dblue
from tools.exec_code.exec_python_linux import execute_python_code_in_docker

class Code_Tool(Base_Tool):
    name='Code_Tool'
    description=\
'''通过python进行编程的工具，该工具的具体要求包括，
1)输入：通过参数code输入python程序，程序必须从新的一行顶格开始，编写程序时要一步一步想清楚。
2)返回：为了获得代码的具体运行结果，代码必须要用print将需要返回的变量打印出来：
print({
    'name':'返回内容的名称',
    'value':需要返回的所有内容数据都放在这里,
})'''
    parameters=[
        {
            'name': 'code',
            'type': 'string',
            'description': \
'''
1）本参数为输入的python代码字符串，必须以"""和"""囊括起来，绝对不能用```或\'\'\'。
2）代码字符串内部的引号用\'对或用\'\'\'对。
''',
            'required': 'True',
        },
    ]
    def __init__(self):
        pass

    def call(self, in_thoughts):
        dict_string = extract_dict_string(in_thoughts)
        code = extract_code(dict_string)
        action_result = execute_python_code_in_docker(code)
        return action_result
