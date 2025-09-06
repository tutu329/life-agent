from abc import ABC, abstractmethod
from typing import Dict, List
from utils.extract import extract_tool_dict

from agent.core.agent_config import Agent_Config
from agent.tools.protocol import Tool_Context
# from agent.core.legacy_protocol import Tool_Context
from agent.tools.protocol import Tool_Call_Paras
from utils.decorator import timer

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


PROMPT_REACT_2025_05_19 = """###你必须回答接下来的问题，而且系统已经为你准备了以下工具，你可以直接访问这些工具:
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

PROMPT_TOOL_CALL = """<总体要求>
你的角色：你是智能化系统的流程控制和优化专家。
你的任务：必须根据【用户问题】调用合适工具或回答问题。
你的回复要求：严格根据【回复流程及格式要求】进行回复，要注意，整个回复流程是一个规划和行动迭代的过程，具体迭代过程为：
    a）工具调用：你根据要求给出一个工具的调用（通常需要先调用【规划和反思工具】，为后续可能的多步工具调用做好充分的分析和优化或根据历史工具调用结果进行反思和调整)）；
    b）观察：这一步由系统完成，系统会强制调用你所选择的工具，并返回工具调用结果供你观察；
    c）工具调用结果分析：你要严格根据系统返回的工具调用结果，进行分析，为后续工具调用做准备；
    d）最终答复：仅当你认为返回的结果已经解决了【用户问题】时，需要给出【最终答复】
</总体要求>

<观察>(这里系统会自动写入工具调用结果信息)
{tool_call_result_list}
</观察>

<用户问题>
{query}
</用户问题>

<用户经验>
{user_experience}
</用户经验>

现在请根据上述需求和情况，调用合适的工具。
"""

PROMPT_REACT = """<总体要求>
你的角色：你是智能化系统的流程控制和优化专家。
你的任务：必须回答【用户问题】，而且系统已经为你准备了【工具集】，你可以调用其中的工具，但要严格根据【工具描述】访问合适的工具。
你的回复要求：严格根据【回复流程及格式要求】进行回复，要注意，整个回复流程是一个规划和行动迭代的过程，具体包括：
    1）规划：你根据【用户问题】，且一定要注意【用户经验】的重要性，给出总体解决思路和工具调用规划。
    2）迭代过程：
        a）工具调用申请：你根据规划，给出一个工具调用申请（包括工具的具体输入参数）；
        b）观察(返回工具调用结果)：这一步由系统根据你的工具调用申请，强制执行对应工具，并返回工具调用结果；
        c）工具调用结果分析：你要严格根据系统返回的工具调用结果，对你之前的工具调用申请参数、甚至规划进行分析和调整；
        d）最终答复：仅当你觉得返回的结果已经解决【用户问题】时，需要给出【最终答复】
</总体要求>

<工具集>
{tool_descs}
</工具集>

<回复流程及格式要求>
[规划]这里写你关于【用户问题】的总体解决思路和工具调用规划，要调理清晰、逻辑精确。

[工具调用申请]这里你写:
{{
    'tool_invoke':'no'或者'yes',
    'tool_name':你所要调用的工具的名称,    (注意工具名称必须是这些名称之一 [{tool_names}] 。)
    'tool_parameters':{{
        'para1' : value1,
        'para2' : value2,   （注意：如果'value'值为代码字符串，则代码字符串起始必须换一行顶格，绝对不能有额外缩进。）
        ... , 
    }},
}}

[观察]这里不能由你写，系统会自动在这里写入工具调用结果信息。

###... (这个 思考/工具调用/工具调用的输入/观察 的流程，可以被重复0次或多次，只要你觉得可以给出最终答复，就要结束这个流程，防止不断循环。)

[工具调用结果分析]这里写你的分析和可能的调整，调理一定要清晰。

[最终答复]只有问题已经解决，你才能写这个最终答复，调理一定要清晰。

</回复流程及格式要求>

<用户问题>
{query}
</用户问题>

<用户经验>
{user_experience}
</用户经验>

现在你开始回复：
"""

# ，且必须以'''和'''囊括起来，绝对不能用```或\"\"\"，且代码字符串内部的引号用\"对或用\"\"\"对


#     tool_name= 'Folder_Tool'
#     tool_description=\
# '''返回指定文件夹下所有文件和文件夹的名字信息。
# '''
#     tool_parameters=[
#         {
#             'name': 'dir',
#             'type': 'string',
#             'description': \
# '''
# 本参数为文件夹所在的路径
# ''',
#             'required': 'True',
#         },
#     ]


class Base_Tool(ABC):
    tool_name: str
    tool_description: str
    tool_parameters: List[Dict]

    def __init__(self):
        pass

    # ------------用于agent_as_tool------------
    def set_cancel(self):
        pass
    def unset_cancel(self):
        pass
    def is_canceling(self):
        pass
    # -----------/用于agent_as_tool------------

    @abstractmethod
    def call(self, tool_call_paras:Tool_Call_Paras):
    # def call(
    #         self,
    #         callback_tool_paras_dict,               # agent调用tool时的输入参数
    #         callback_agent_config:Agent_Config,           # agent配置参数
    #         callback_agent_id,                      # agent_id
    #         callback_last_tool_ctx:Tool_Context,    # 上一个tool的上下文context(包含tool_task_id和可能的dataset_info)
    # ):
        pass

    # 将Tool类转为openai的tool参数
    @classmethod
    def get_tool_param_dict(cls):
        tool_param_dict = {
            "type": "function",
            "name": cls.tool_name,
            "description": cls.tool_description,
            "strict": True,  # 让模型严格遵循 JSON Schema
            "parameters": cls.tool_parameters,
        }
        return tool_param_dict

    @classmethod
    def extract_tool_name_from_answer(cls, in_answer):
        try:
            # # print(f'+++++++++++++++++++++thoughts in extract_tool_name() is : \n{in_answer}+++++++++++++++++++++')
            # dict_string = legacy_extract_dict_string(in_answer)
            # # dict_string = legacy_extract_dict_string(in_answer)
            # # print(f'+++++++++++++++++++++dict_string in extract_tool_name() is : \n{dict_string}+++++++++++++++++++++')
            # if not dict_string:
            #     print(Fore.RED, flush=True)
            #     print(f'dict_string为空', flush=True)
            #     print('返回tool_name=""', flush=True)
            #     print(Style.RESET_ALL, flush=True)
            #     return ''
            #
            # # 过滤掉可能存在的代码
            # code = extract_code(dict_string)
            # dict_string__ = dict_string.replace(code, "")
            # dict_string__ = dict_string__.replace('""""""', "''")
            #
            # # 去掉'[观察]'及后续内容
            # # dict_string__ = dict_string__.split('[观察]')
            # # dict_string__.pop()
            # # dict_string__ = ''.join(dict_string__)
            #
            # dprint('-----------dict string to get tool_name is:----------')
            # dprint(dict_string__)
            # dprint('-----------------------------------------------------')
            #
            # dict = json5.loads(dict_string__)

            dict = extract_tool_dict(in_answer)

            # print(f'+++++++++++++++++++++dict in extract_tool_name() is : \n{dict}+++++++++++++++++++++')
            rtn = dict['tool_name']
        except Exception as e:
            # print(Fore.RED, flush=True)
            # print(f'extract_tool_name()错误: "{e}"', flush=True)
            # print(f'full answer is: "{in_answer}"')
            # print('返回tool_name=""', flush=True)
            # print(Style.RESET_ALL, flush=True)
            error_result_list = ['error', f'工具调用失败！原因是你未输出工具调用申请信息，或者你输出的工具选择信息解析出现错误，你输出的需解析的全部文本为"{in_answer}", 报错信息为"{e}"']
            rtn = error_result_list
        return rtn