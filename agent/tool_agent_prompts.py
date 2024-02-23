from typing import Dict, List, Union

from tools.exec_code.exec_python_linux import execute_python_code_in_docker
from utils.extract import extract_code, extract_dict_string
from tools.retriever.search import Bing_Searcher

import json5

PROMPT_REACT0 = """Answer the following questions as best you can. You have access to the following tools:

{tool_descs}Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can be repeated zero or more times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {query}"""

PROMPT_REACT = """你必须回答接下来的问题，而且系统已经为你准备了以下这些工具，你可以直接访问这些工具:
{tool_descs}

回复格式具体如下:

【问题】需要你回答的问题。
【思考】这里写你的思考过程，关于如何才能更好的回答这个问题。
【工具】这里写{{
    'tool_invoke':'no'或者'yes',
    'tool_name':你所要调用的工具的名称,
    'tool_parameters':[
        {{'name':参数名称, 'value':参数值}}, （注意：如果'value'值为代码字符串，则代码字符串起始必须换一行顶格，绝对不能有额外缩进。）
        ... , 
    ],
}}。(注意工具名称必须是这些名称之一 [{tool_names}] 。)
【观察】这里不需要你写，系统会自动在这里提供工具调用的结果信息。

... (这个 思考/工具调用/工具调用的输入/观察 的流程，可以被重复0次或多次，直到观察结果表明能够得到最终答复)

【思考】这里写你对最终答复的思考过程。
【最终答复】这里写你需要回答的问题的最终答复。

现在开始!

【问题】{query}"""

class Base_Tool():
    name: str
    description: str
    parameters: List[Dict]

    def __init__(self):
        pass

    def call(self):
        pass

    @classmethod
    def extract_tool_name(cls, in_thoughts):
        dict_string = extract_dict_string(in_thoughts)
        if not dict_string:
            return ''
        # print('+++++++++++++++++++++')
        
        # print(f'dict_string:')
        # print(f'{dict_string}')
        
        # print(f'dict:')
        # 过滤掉可能存在的代码
        code = extract_code(dict_string)
        dict_string__ = dict_string.replace(code, "")
        dict_string__ = dict_string__.replace('""""""', "''")
        # print(f'code:')
        # print(f'{code}')
        # print(f'dict_string__:')
        # print(f'{dict_string__}')
        dict = json5.loads(dict_string__)
        # print(f'{dict}')
        
        # print('+++++++++++++++++++++')
        
        return dict['tool_name']

class Search_Tool(Base_Tool):
    name='search_tool'
    description='通过bing.com进行网页搜索并通过playwright爬取搜索结果的工具.'
    parameters=[
        {
            'name': 'query',
            'type': 'string',
            'description': '搜索的关键词',
            'required': 'True',
        },
    ]
    def __init__(self):
        pass

    def call(self, in_thoughts):
        dict_string = extract_dict_string(in_thoughts)
        dict = json5.loads(dict_string)
        query = dict['tool_parameters'][0]['value']
        print(f'Search_Tool.call(): dict obj is: {dict}')
        print(f'Search_Tool.call(): query is: "{query}"')

        searcher = Bing_Searcher.create_searcher_and_loop(in_search_num=3)
        gen = searcher.search_and_ask_yield(query, in_max_new_tokens=1024)
        action_result = ''
        for res in gen:
            chunk = res['response']
            if res['response_type']=='final':
                print(chunk, end='', flush=True)
                action_result += chunk
        return action_result

class Code_Tool(Base_Tool):
    name='code_tool'
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
