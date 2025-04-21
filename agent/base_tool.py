from abc import ABC, abstractmethod
from typing import Dict, List
from utils.extract import extract_code, extract_dict_string
from colorama import Fore, Style
import json5

from agent.agent_config import Config

DEBUG = False
# DEBUG = True

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)
    else:
        pass

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

PROMPT_REACT_2024_03_21 = """你必须回答接下来的问题，而且系统已经为你准备了以下这些工具，你可以直接访问这些工具:
{tool_descs}

回复必须严格按照如下格式:

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

PROMPT_REACT11 = """你必须回答接下来的问题，而且系统已经为你准备了以下这些工具，你可以直接访问这些工具:
{tool_descs}

回复必须严格按照如下格式:

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
<结束> (注意这是中止标志，你必须要写)

[观察]这里不需要你写，系统会自动在这里提供工具调用的结果信息。

... (这个 思考/工具调用/工具调用的输入/观察 的流程，可以被重复0次或多次，只要你觉得可以给出最终答复，就要结束这个流程，防止不断循环。)

[最终答复]这里写你需要回答的问题的最终答复，调理一定要清晰，要用markdown进行格式化。

现在开始!

[问题]{query}"""

PROMPT_REACT01 = """###你必须回答接下来的问题，而且系统已经为你准备了以下工具，你可以直接访问这些工具:
{tool_descs}

###回复要求为:
1)若能给出最终答复，则回复:
[观察]
{{
    'observer':'llm',
    'status':'最终答复',
    'result':你的最终答复,
}}
<结束> (这个结束必须要有)

2)若不能给出最终答复，还需要调用工具，则回复(另外，你绝对不能代替系统给出结果)：
[工具]
{{
    'tool_invoke':'no'或者'yes',
    'tool_name':你所要调用的工具的名称,
    'tool_parameters':{{
        'para1' : value1,
        'para2' : value2,   （注意：如果'value'值为代码字符串，则代码字符串起始必须换一行顶格，绝对不能有额外缩进。）
        ... , 
    }},
}}
[观察]
{{
    'observer':'llm',		(注意：这里你写'llm'，如果是系统回复的，会填写'system')
    'status':'等系统回复',
    'result':'',		    (系统回复的内容将会填在这里)
}}
<结束> (这个结束必须要有)

###... (这个 工具/观察 的流程，可以被重复0次或多次，如果你觉得可以给出最终答复，就要结束这个流程，防止不断循环。)

###现在开始!

[问题]{query}"""


PROMPT_REACT = """###你必须回答接下来的问题，而且系统已经为你准备了以下工具，你可以直接访问这些工具:
{tool_descs}

回复格式具体如下:

[问题]需要你回答的问题。

[思考]这里写你的思考过程，关于如何才能更好的回答这个问题。

[工具]这里你写:
{{
    'tool_invoke':'no'或者'yes',
    'tool_name':你所要调用的工具的名称,    (注意工具名称必须是这些名称之一 [{tool_names}] 。)
    'tool_parameters':{{
        'para1' : value1,
        'para2' : value2,   （注意：如果'value'值为代码字符串，则代码字符串起始必须换一行顶格，绝对不能有额外缩进。）
        ... , 
    }},
}}

[观察]这里不能由你写，系统会自动在这里提供工具调用的结果信息。

###... (这个 思考/工具调用/工具调用的输入/观察 的流程，可以被重复0次或多次，只要你觉得可以给出最终答复，就要结束这个流程，防止不断循环。)

[最终答复]这里写你需要回答的问题的最终答复，调理一定要清晰。

###现在开始!

[问题]{query}"""

class Base_Tool(ABC):
    name: str
    description: str
    parameters: List[Dict]

    def __init__(self):
        pass

    @abstractmethod
    def call(self,
             in_thoughts,
             agent_config:Config,
             # in_is_web_server=True,
             # in_client_data_sse_stream_buf=None,
             ):
        pass

    @classmethod
    def extract_tool_name_from_answer(cls, in_answer):
        try:
            # print(f'+++++++++++++++++++++thoughts in extract_tool_name() is : \n{in_answer}+++++++++++++++++++++')
            dict_string = extract_dict_string(in_answer)
            # print(f'+++++++++++++++++++++dict_string in extract_tool_name() is : \n{dict_string}+++++++++++++++++++++')
            if not dict_string:
                print(Fore.RED, flush=True)
                print(f'dict_string为空', flush=True)
                print('返回tool_name=""', flush=True)
                print(Style.RESET_ALL, flush=True)
                return ''


            # print(f'dict:')
            # 过滤掉可能存在的代码
            # print('-----extract_tool_name1------')
            code = extract_code(dict_string)
            # print(f'****** code:\n{code}\n*****')
            # print('-----extract_tool_name2------')
            dict_string__ = dict_string.replace(code, "")
            # print('-----extract_tool_name3------')
            dict_string__ = dict_string__.replace('""""""', "''")
            # print('-----extract_tool_name4------')

            # 去掉'[观察]'及后续内容
            # dict_string__ = dict_string__.split('[观察]')
            # dict_string__.pop()
            # dict_string__ = ''.join(dict_string__)

            dprint('-----------dict string to get tool_name is:----------')
            dprint(dict_string__)
            dprint('-----------------------------------------------------')

            dict = json5.loads(dict_string__)
            # print('-----extract_tool_name5------')


            # print(f'+++++++++++++++++++++dict in extract_tool_name() is : \n{dict}+++++++++++++++++++++')
            rtn = dict['tool_name']
        except Exception as e:
            print(Fore.RED, flush=True)
            print(f'extract_tool_name()错误: "{e}"', flush=True)
            print('返回tool_name=""', flush=True)
            print(Style.RESET_ALL, flush=True)
            return ""

        return rtn