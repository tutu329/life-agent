from typing import Dict, List, Union

from tools.exec_code.exec_python_linux import execute_python_code_in_docker
from utils.extract import extract_code, extract_dict_string
from tools.retriever.search import Bing_Searcher
from config import Global

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

PROMPT_REACT_2024_02_26 = """你必须回答接下来的问题，而且系统已经为你准备了以下这些工具，你可以直接访问这些工具:
{tool_descs}

回复格式具体如下:

[问题]需要你回答的问题。
[思考]这里写你的思考过程，关于如何才能更好的回答这个问题。
[工具]这里写{{
    'tool_invoke':'no'或者'yes',
    'tool_name':你所要调用的工具的名称,
    'tool_parameters':{{
        'para1' : value1,
        'para2' : value2,   （注意：如果'value'值为代码字符串，则代码字符串起始必须换一行顶格，绝对不能有额外缩进。）
        ... , 
    }},
}}。(注意工具名称必须是这些名称之一 [{tool_names}] 。)
[观察]这里不需要你写，系统会自动在这里提供工具调用的结果信息。

... (这个 思考/工具调用/工具调用的输入/观察 的流程，可以被重复0次或多次，直到观察结果表明能够得到最终答复)

[思考]这里写你对最终答复的思考过程。
[最终答复]这里写你需要回答的问题的最终答复，调理一定要清晰，要用markdown进行格式化。

现在开始!

[问题]{query}"""

PROMPT_REACT = """你必须回答接下来的问题，而且系统已经为你准备了以下这些工具，你可以直接访问这些工具:
{tool_descs}

回复格式具体如下:

[问题]需要你回答的问题。
[思考]这里写你的思考过程，关于如何才能更好的回答这个问题。
[工具]这里写{{
    'tool_invoke':'no'或者'yes',
    'tool_name':你所要调用的工具的名称,
    'tool_parameters':{{
        'para1' : value1,
        'para2' : value2,   （注意：如果'value'值为代码字符串，则代码字符串起始必须换一行顶格，绝对不能有额外缩进。）
        ... , 
    }},
}}。(注意工具名称必须是这些名称之一 [{tool_names}] 。)
[观察]这里不需要你写，系统会自动在这里提供工具调用的结果信息。

... (这个 思考/工具调用/工具调用的输入/观察 的流程，可以被重复0次或多次，只要你觉得可以给出最终答复，就要结束这个流程，防止不断循环。)

[最终答复]这里写你需要回答的问题的最终答复，调理一定要清晰，要用markdown进行格式化。

现在开始!

[问题]{query}"""

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

class Energy_Investment_Plan_Tool(Base_Tool):
    name='energy_investment_plan_tool'
    description='''
通过"能源投资优化系统"对风光储等能源设施进行基于线性规划的最优投资规模计算的工具.
所输入参数必须遵循如下要求, 否则转换为dict数据时会失败:
1)绝对不能增加如#开头的注释.
2)bool变量必须为true或false, 而不能是True或False.
'''
    parameters=[
        {
            'name': 'rate',
            'type': 'float',
            'description': '基准收益率',
            'required': 'True',
        },
        {
            'name': 'simu_years',
            'type': 'int',
            'description': '仿真年数(年)',
            'required': 'True',
        },
        {
            'name': 'load_max',
            'type': 'float',
            'description': '最大负荷(kW)',
            'required': 'True',
        },
        {
            'name': 'load_electricity',
            'type': 'float',
            'description': '年用电量(kWh)',
            'required': 'True',
        },
        {
            'name': 'storage_w_cost',
            'type': 'float',
            'description': '储能系统的功率单位造价(元/W)',
            'required': 'True',
        },
        {
            'name': 'storage_wh_cost',
            'type': 'float',
            'description': '储能系统的容量单位造价(元/Wh)',
            'required': 'True',
        },
        {
            'name': 'pv_cost',
            'type': 'float',
            'description': '光伏系统的功率单位造价(元/W)',
            'required': 'True',
        },
        {
            'name': 'pv_nom0',
            'type': 'float',
            'description': '已建光伏系统规模(kW)',
            'required': 'True',
        },
        {
            'name': 'pv_optimize',
            'type': 'bool',
            'description': '是否对光伏系统新建规模进行优化(true|false)',
            'required': 'True',
        },
        {
            'name': 'wind_cost',
            'type': 'float',
            'description': '风电系统的功率单位造价(元/W)',
            'required': 'True',
        },
        {
            'name': 'wind_nom0',
            'type': 'float',
            'description': '已建风电系统规模(kW)',
            'required': 'True',
        },
        {
            'name': 'wind_optimize',
            'type': 'bool',
            'description': '是否对风电系统新建规模进行优化(true|false)',
            'required': 'True',
        },
        {
            'name': 'up_flow_max_proportion',
            'type': 'float',
            'description': '新能源倒送到电网的电量的最大比例(0.0-1.0)',
            'required': 'True',
        },
        {
            'name': 'down_flow_max_proportion',
            'type': 'float',
            'description': '电网下送电量的最大比例(0.0-1.0)',
            'required': 'True',
        },
    ]
    def __init__(self):
        pass

    def call(self, in_thoughts):
        dict_string = extract_dict_string(in_thoughts)
        dict = json5.loads(dict_string)
        print(Global.line)
        print(f'Energy_Investment_Plan_Tool的输入参数dict为: {dict}')
        print(Global.line)

        action_result = ''
        try:
            import requests
            from requests.exceptions import RequestException
            # req = {
            #     'rate': 0.08,
            #
            #     'pv_nom0': 0,
            #     'pv_cost': 3.5,
            #     'pv_optimize': True,
            #
            #     'wind_nom0': 0,
            #     'wind_cost': 3.5,
            #     'wind_optimize': True,
            #
            #     'storage_w_cost': 0.12,
            #     'storage_wh_cost': 1.38 * 0.6,
            #
            #     'up_flow_max_proportion': 0.2,
            #     'down_flow_max_proportion': 0.1,
            #
            #     'load_max': 800 * 1000,
            #     'load_electricity': 800 * 1000 * 6400,
            #
            #     'simu_years': 10,
            # }
            req = dict['tool_parameters']
            response = requests.post(url='http://116.62.63.204:18001/cal/', json=req)
            response.raise_for_status()  # 如果不在200-400，发出一个异常
            rtn_table = response.json()
            # print(f'NPS服务器返回的结果为: \n{rtn_table}')
        except RequestException as e:
            action_result = f'Energy_Investment_Plan_Tool请求API时，服务器报错：{e}'

        # action_result = f'Energy_Investment_Plan_Tool返回的结果汇总为: \n{rtn_table}'
        action_result = f'Energy_Investment_Plan_Tool返回的结果汇总为: \n{rtn_table}\n 请返回整理结果和报告url'
        # action_result = '[最终答复]Energy_Investment_Plan_Tool()尚未完整实现.'
        return action_result

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
        query = dict['tool_parameters']['query']
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
