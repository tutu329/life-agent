import asyncio
from pathlib import Path

from openai import OpenAI, APIError
from openai.types.responses import ResponseReasoningItem, ResponseFunctionToolCall, ResponseOutputMessage
from openai.types.responses import ToolParam, FunctionToolParam

from pprint import pprint
import httpx, os, json
from sympy.testing.tests.test_code_quality import message_func_is

from agent.tools.folder_tool import Folder_Tool


# 关于vllm api允许gpt-oss模型在thinking中调用built-in工具：
# pip install gpt-oss(gpt-oss>=0.0.5，需python3.12)
# $ export PYTHON_EXECUTION_BACKEND=dangerously_use_uv
# $ vllm serve openai/gpt-oss-20b --async-scheduling --tool-server demo

# stream方式的llm调用
def llm_simple():
    print('started...')

    http_client = httpx.Client(proxy="http://127.0.0.1:7890")

    client = OpenAI(
        api_key='empty',
        base_url='http://powerai.cc:18002/v1',
    )
    gen = client.responses.create(
        model='gpt-oss-20b-mxfp4',
        temperature=1.0,
        # temperature=0.6,
        top_p=1.0,
        # top_p=0.95,
        instructions='You are a helpful assistant.',

        # input='我叫土土，帮我写一首简短的爱情诗',
        # input = query,
        input='今天杭州天气如何？',
        stream=True,

        max_output_tokens=8192,
        reasoning={"effort": 'low'},
    )

    # client = OpenAI(
    #     api_key=os.getenv("GROQ_API_KEY") or 'empty',
    #     base_url='https://api.groq.com/openai/v1',
    #     http_client=http_client,
    #     # http_client=openai.DefaultHttpxClient(verify=False),  # 用于自建的vllm openai api的ssl访问(https访问)， # 阿里云购买了正式证书（可以是免费的）后，即可开启verify，也就是去掉本行
    # )
    #
    # gen = client.responses.create(
    #     model='openai/gpt-oss-20b',
    #     # model='openai/gpt-oss-120b',
    #     temperature=0.6,
    #     top_p=0.95,
    #     instructions='You are a helpful assistant.',
    #
    #     # input='我叫土土，帮我写一首简短的爱情诗',
    #     # input = query,
    #     input='今天杭州天气如何？',
    #     stream=True,
    #
    #     max_output_tokens=8192,
    #     reasoning={"effort": 'low'},
    # )

    thinking_started = False
    result_started = False

    for chunk in gen:
        # print(f'chunk: "{chunk}"')
        if (chunk.type and chunk.type == "response.reasoning_text.delta"):
            if not thinking_started:
                print('\n【thinking】')
                thinking_started = True
            print(f'{chunk.delta}', end='', flush=True)
        elif (chunk.type and chunk.type == "response.output_text.delta"):
            if not result_started:
                print('\n\n【result】')
                result_started = True
            print(f'{chunk.delta}', end='', flush=True)

        elif (chunk.type and chunk.type in ("function_call", "tool_call")):
            print('tool invoded.')
    print()


# 非stream方式的tool_call调用（harmony的tool call调用不支持stream）
# def llm_tool_call(last_answer=''):
#     print('\n============================================================================================================')
#     print('=================================================【started】=================================================')
#     print('============================================================================================================\n')
#
#     http_client = httpx.Client(proxy="http://127.0.0.1:7890")
#
#     # client = OpenAI(
#     #     api_key='empty',
#     #     base_url='http://powerai.cc:18002/v1',
#     # )
#
#     client = OpenAI(
#         api_key=os.getenv("GROQ_API_KEY") or 'empty',
#         base_url='https://api.groq.com/openai/v1',
#         http_client=http_client,
#         # http_client=openai.DefaultHttpxClient(verify=False),  # 用于自建的vllm openai api的ssl访问(https访问)， # 阿里云购买了正式证书（可以是免费的）后，即可开启verify，也就是去掉本行
#     )
#     query = '<总体要求>\n你的角色：你是智能化系统的流程控制和优化专家。\n你的任务：必须回答【用户问题】，而且系统已经为你准备了【工具集】，你可以调用其中的工具，但要严格根据【工具描述】访问合适的工具。\n你的回复要求：严格根据【回复流程及格式要求】进行回复，要注意，整个回复流程是一个规划和行动迭代的过程，具体包括：\n    1）规划：你根据【用户问题】，且一定要注意【用户经验】的重要性，给出总体解决思路和工具调用规划。\n    2）迭代过程：\n        a）工具调用申请：你根据规划，给出一个工具调用申请（包括工具的具体输入参数）；\n        b）观察(返回工具调用结果)：这一步由系统根据你的工具调用申请，强制执行对应工具，并返回工具调用结果；\n        c）工具调用结果分析：你要严格根据系统返回的工具调用结果，对你之前的工具调用申请参数、甚至规划进行分析和调整；\n        d）最终答复：仅当你觉得返回的结果已经解决【用户问题】时，需要给出【最终答复】\n</总体要求>\n\n<工具集>\n工具名称: Folder_Tool\n工具描述: 返回指定文件夹下所有文件和文件夹的名字信息。\n\n工具参数: [\n\t{\t参数名称: dir,\n\t\t参数类型: string,\n\t\t参数描述: \n本参数为文件夹所在的路径\n,\n\t\t参数是否必需: True,\n\t},\n]\n\n\n</工具集>\n\n<回复流程及格式要求>\n[规划]这里写你关于【用户问题】的总体解决思路和工具调用规划，要调理清晰、逻辑精确。\n\n[工具调用申请]这里你写:\n{\n    \'tool_invoke\':\'no\'或者\'yes\',\n    \'tool_name\':你所要调用的工具的名称,    (注意工具名称必须是这些名称之一 [\'Folder_Tool\'] 。)\n    \'tool_parameters\':{\n        \'para1\' : value1,\n        \'para2\' : value2,   （注意：如果\'value\'值为代码字符串，则代码字符串起始必须换一行顶格，绝对不能有额外缩进。）\n        ... , \n    },\n}\n\n[观察]这里不能由你写，系统会自动在这里写入工具调用结果信息。\n\n###... (这个 思考/工具调用/工具调用的输入/观察 的流程，可以被重复0次或多次，只要你觉得可以给出最终答复，就要结束这个流程，防止不断循环。)\n\n[工具调用结果分析]这里写你的分析和可能的调整，调理一定要清晰。\n\n[最终答复]只有问题已经解决，你才能写这个最终答复，调理一定要清晰。\n\n</回复流程及格式要求>\n\n<用户问题>\n我叫土土，请告诉我"file_to_find.txt"在"/home/tutu/demo/"文件夹的哪个具体文件夹中，要仔细搜索其子文件夹。\n</用户问题>\n\n<用户经验>\n\n</用户经验>\n\n现在你开始回复：\n'
#
#
#     # legacy_tools = [
#     #     # {"type": "python", "container": {"type": "auto"}},
#     #     # {"type": "code_interpreter", "container": {"type": "auto"}},
#     #     {
#     #         "type": "function",
#     #         "name": "get_weather",
#     #         "description": "Get current weather in a given city",
#     #         "strict": True,  # 让模型严格遵循 JSON Schema
#     #         "parameters": {
#     #             "type": "object",
#     #             "properties": {
#     #                 "city": {"type": "string", "description": "City name"},
#     #                 "unit": {"type": "string", "description": "temperature unit", "enum": ["c", "f"]},
#     #             },
#     #             "required": ["city"],
#     #             "additionalProperties": False,
#     #         },
#     #     },
#     #     {
#     #         "type": "function",
#     #         "name": "Folder_Tool",
#     #         "description": "获取当前目录下的子文件夹清单和文件清单",
#     #         "strict": True,  # 让模型严格遵循 JSON Schema
#     #         "parameters": {
#     #             "type": "object",
#     #             "properties": {
#     #                 "path": {"type": "string", "description": "文件夹的路径"},
#     #             },
#     #             "required": ["path"],
#     #             "additionalProperties": False,
#     #         },
#     #     }
#     # ]
#
#     tools = [
#         # {"type": "python", "container": {"type": "auto"}},
#         # {"type": "code_interpreter", "container": {"type": "auto"}},
#         {
#             "type": "function",
#             "name": "get_weather",
#             "description": "Get current weather in a given city",
#             "strict": True,  # 让模型严格遵循 JSON Schema
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "city": {"type": "string", "description": "City name"},
#                     "unit": {"type": "string", "description": "temperature unit", "enum": ["c", "f"]},
#                 },
#                 "required": ["city"],
#                 "additionalProperties": False,
#             },
#         },
#         Folder_Tool.get_tool_param_dict(),
#         # {
#         #     "type": "function",
#         #     "name": "Folder_Tool",
#         #     "description": "获取当前目录下的子文件夹清单和文件清单",
#         #     "strict": True,  # 让模型严格遵循 JSON Schema
#         #     "parameters": {
#         #         "type": "object",
#         #         "properties": {
#         #             "path": {"type": "string", "description": "文件夹的路径"},
#         #         },
#         #         "required": ["path"],
#         #         "additionalProperties": False,
#         #     },
#         # }
#     ]
#
#     # input='我叫土土，帮我写一首简短的爱情诗'
#     input = '告诉我杭州天气如何，并且告诉我"file_to_find.txt"在"/home/tutu/demo/"文件夹的哪个具体文件夹中'
#     # input='请告诉我"file_to_find.txt"在"/home/tutu/demo/"文件夹的哪个具体文件夹中，并且告诉我1+1=？'
#     # input='告诉我1+1=？'
#     # input='今天杭州天气如何？'
#     # input='Multiply 64548*15151 using builtin python interpreter.'
#     # input='计算一下1234/4567等于多少，保留10位小数'
#     # input = query
#
#     input = last_answer + '\n' + input
#     print('---------------------input--------------------')
#     print(input)
#     print('--------------------/input--------------------\n')
#
#     res = client.responses.create(
#         # model='gpt-oss-20b-mxfp4',
#         model='openai/gpt-oss-20b',
#         # model='openai/gpt-oss-120b',
#         temperature=1.0,
#         # temperature=0.6,
#         top_p=1.0,
#         # top_p=0.95,
#         instructions='You are a helpful assistant.',
#         input=input,
#
#         tools=tools,
#         tool_choice="auto",
#         parallel_tool_calls=False,
#         stream=False,
#
#         max_output_tokens=8192,
#         reasoning={"effort": 'low'},
#     )
#
#     thinking_started = False
#     result_started = False
#     tool_args = None
#     tool_name = ''
#
#     message_result = ''
#     result_type = ''
#
#     if res.output:
#         count = 0
#         for item in res.output:
#             print(f'【item{count}】 "{item}"')
#             count += 1
#
#         count = 0
#         for item in res.output:
#             if isinstance(item, ResponseFunctionToolCall):
#                 print(f'------------------【item{count}】ResponseFunctionToolCall-------------------')
#                 pprint(item.model_dump(), sort_dicts=False, width=120)
#                 if item.type in ('function_call', 'tool_call'):
#                     tool_args = json.loads(item.arguments)
#                     tool_name = item.name
#                 print(f'-----------------/【item{count}】ResponseFunctionToolCall-------------------')
#             elif isinstance(item, ResponseReasoningItem):
#                 print(f'-------------------【item{count}】ResponseReasoningItem---------------------')
#                 pprint(item.model_dump(), sort_dicts=False, width=120)
#                 print(f'------------------/【item{count}】ResponseReasoningItem---------------------')
#             elif isinstance(item, ResponseOutputMessage):
#                 # print(f'-------------------【item{count}】ResponseOutputMessage---------------------')
#                 # pprint(item.model_dump(), sort_dicts=False, width=120)
#                 message_result = item.content[0].text
#                 result_type = item.content[0].type
#                 # print(f'------------------/【item{count}】ResponseOutputMessage---------------------')
#             else:
#                 print(f'------------------------【item{count}】other item---------------------------')
#                 pprint(item.model_dump(), sort_dicts=False, width=120)
#                 print(f'-----------------------/【item{count}】other item---------------------------')
#             count += 1
#
#     def get_weather(city: str, unit: str = 'c') -> dict:
#         # 这里替换为真实实现
#         return {"city": city, "temperature_c": 23, "unit": unit, "status": "sunny"}
#
#     tool_result = ''
#     if tool_args:
#         print(f'\n------------------------【调用工具】---------------------------')
#         print(f'调用工具"{tool_name}"，参数为: {tool_args!r}')
#         if tool_name == 'get_weather':
#             tool_result = get_weather(**tool_args)
#             print(tool_result)
#         print(f'-----------------------/【调用工具】---------------------------')
#
#     if message_result:
#         print(f'\n------------------------【输出结果】(type: {result_type})---------------------------')
#         print(message_result)
#         print(f'-----------------------/【输出结果】---------------------------')
#
#     return '工具调用结果为：' + json.dumps(tool_result) + '\n'
#     # return '工具调用结果为：' + json.dumps(tool_result) + '\n' + f'分析结果为：{message_result!r}'

g_tool_call_result_list = []
g_tools_without_plan_str = ''

def tool_call_agent(last_tool_result=None):
    global g_tool_call_result_list, g_tools_without_plan_str

    from agent.tools.base_tool import PROMPT_TOOL_CALL
    from copy import deepcopy

    http_client = httpx.Client(proxy="http://127.0.0.1:7890")
    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY") or 'empty',
        base_url='https://api.groq.com/openai/v1',
        http_client=http_client,
    )

    # tools_with_plan = [
    #     {
    #         "type": "function",
    #         "name": "plan_tool",
    #         "description": "根据用户要求，对后续工具调用进行总体规划和优化。",
    #         "strict": True,  # 让模型严格遵循 JSON Schema
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "user_query": {"type": "string", "description": "用户需求"},
    #             },
    #             "required": ['user_query'],
    #             "additionalProperties": False,
    #         },
    #     },
    #     {
    #         "type": "function",
    #         "name": "add_tool",
    #         "description": "计算两个数的和",
    #         "strict": True,  # 让模型严格遵循 JSON Schema
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "a": {"type": "number", "description": "a"},
    #                 "b": {"type": "number", "description": "b"},
    #             },
    #             "required": [],
    #             "additionalProperties": False,
    #         },
    #     },
    #     {
    #         "type": "function",
    #         "name": "sub_tool",
    #         "description": "计算两个数的差",
    #         "strict": True,  # 让模型严格遵循 JSON Schema
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "a": {"type": "number", "description": "a"},
    #                 "b": {"type": "number", "description": "b"},
    #             },
    #             "required": [],
    #             "additionalProperties": False,
    #         },
    #     },
    #     {
    #         "type": "function",
    #         "name": "multiple_tool",
    #         "description": "计算两个数的积",
    #         "strict": True,  # 让模型严格遵循 JSON Schema
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "a": {"type": "number", "description": "a"},
    #                 "b": {"type": "number", "description": "b"},
    #             },
    #             "required": [],
    #             "additionalProperties": False,
    #         },
    #     },
    #     {
    #         "type": "function",
    #         "name": "div_tool",
    #         "description": "计算两个数相除",
    #         "strict": True,  # 让模型严格遵循 JSON Schema
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "a": {"type": "number", "description": "a"},
    #                 "b": {"type": "number", "description": "b"},
    #             },
    #             "required": [],
    #             "additionalProperties": False,
    #         },
    #     },
    #     Folder_Tool.get_tool_param_dict(),
    # ]
    tools = [
        {
            "type": "function",
            "name": "add_tool",
            "description": "计算两个数的和",
            "strict": True,  # 让模型严格遵循 JSON Schema
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "a"},
                    "b": {"type": "number", "description": "b"},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "sub_tool",
            "description": "计算两个数的差",
            "strict": True,  # 让模型严格遵循 JSON Schema
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "a"},
                    "b": {"type": "number", "description": "b"},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "multiple_tool",
            "description": "计算两个数的积",
            "strict": True,  # 让模型严格遵循 JSON Schema
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "a"},
                    "b": {"type": "number", "description": "b"},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "div_tool",
            "description": "计算两个数相除",
            "strict": True,  # 让模型严格遵循 JSON Schema
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "a"},
                    "b": {"type": "number", "description": "b"},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
        Folder_Tool.get_tool_param_dict(),
    ]

    tools_without_plan = deepcopy(tools)
    tools_without_plan.pop(0)  # 去掉plan_tool后，将所有tool描述交给plan_tool
    g_tools_without_plan_str = json.dumps(tools_without_plan)
    # print(f'-------------------------------g_tools_without_plan_str---------------------------------------')
    # for item in tools_without_plan:
    #     print(item)
    # print(f'------------------------------/g_tools_without_plan_str---------------------------------------')

    # input = '请告诉我234+45*56-6/7等于多少' # 2753.142857
    input = '请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算' # 2753.142857
    # input = '请告诉我45346+3486*3344-235644/34等于多少' # 2753.142857
    # input = '请告诉我"file_to_find.txt"在"/home/tutu/demo/"文件夹的哪个具体文件夹中，并且告诉我1+1=？'
    if last_tool_result is None:
        g_tool_call_result_list = []
    else:
        g_tool_call_result_list.append(last_tool_result)

    tool_call_result_str = ''
    count = 0
    for item in g_tool_call_result_list:
        count += 1
        tool_call_result_str += f'第{count}次工具调用，' + item

    PROMPT_TOOL_CALL = PROMPT_TOOL_CALL.format(
        tool_call_result_list=tool_call_result_str,
        # tool_call_result_list='\n'.join(g_tool_call_result_list),
        query=input,
        user_experience='',
    )

    # print(f'------------------------------------------------------PROMPT_TOOL_CALL------------------------------------------------------------------------')
    # print(PROMPT_TOOL_CALL)
    # print(f'-----------------------------------------------------/PROMPT_TOOL_CALL------------------------------------------------------------------------')

    res = client.responses.create(
        # model='gpt-oss-20b-mxfp4',
        # model='openai/gpt-oss-20b',
        model='openai/gpt-oss-120b',
        # temperature=0.6,
        temperature=1.0,
        # top_p=0.95,
        top_p=1.0,
        instructions='You are a helpful assistant.',
        input=PROMPT_TOOL_CALL,

        tools=tools,
        tool_choice="auto",
        parallel_tool_calls=False,
        stream=False,

        max_output_tokens=8192,
        # reasoning={"effort": 'high'},
        # reasoning={"effort": 'medium'},
        reasoning={"effort": 'low'},
    )

    # ----------------------------response格式构建history-------------------------------

    # return await self._client.responses.create(
    #     previous_response_id=self._non_null_or_not_given(previous_response_id),
    #     conversation=self._non_null_or_not_given(conversation_id),
    #     instructions=self._non_null_or_not_given(system_instructions),
    #     model=self.model,
    #     input=list_input,
    #     include=include,
    #     tools=converted_tools.tools,
    #     prompt=self._non_null_or_not_given(prompt),
    #     temperature=self._non_null_or_not_given(model_settings.temperature),
    #     top_p=self._non_null_or_not_given(model_settings.top_p),
    #     truncation=self._non_null_or_not_given(model_settings.truncation),
    #     max_output_tokens=self._non_null_or_not_given(model_settings.max_tokens),
    #     tool_choice=tool_choice,
    #     parallel_tool_calls=parallel_tool_calls,
    #     stream=stream,
    #     extra_headers={**_HEADERS, **(model_settings.extra_headers or {})},
    #     extra_query=model_settings.extra_query,
    #     extra_body=model_settings.extra_body,
    #     text=response_format,
    #     store=self._non_null_or_not_given(model_settings.store),
    #     reasoning=self._non_null_or_not_given(model_settings.reasoning),
    #     metadata=self._non_null_or_not_given(model_settings.metadata),
    #     **extra_args,
    # )

    # 第一次调用后的历史（Responses API格式）：
    # {
    #     "instructions": "You are a helpful agent.",
    #     "input": [
    #         {
    #             "role": "user",
    #             "content": "What's the weather in Tokyo?"
    #         },
    #         {
    #             "type": "message",
    #             "role": "assistant",
    #             "content": [
    #                 {
    #                     "type": "output_text",
    #                     "text": "I'll check the weather in Tokyo."
    #                 }
    #             ]
    #         },
    #         {
    #             "type": "function_call",
    #             "call_id": "call_456",
    #             "name": "get_weather",
    #             "arguments": "{\"city\": \"Tokyo\"}"
    #         },
    #         {
    #             "type": "function_call_output",
    #             "call_id": "call_456",
    #             "output": "Weather(city='Tokyo', temperature_range='14-20C', conditions='Sunny')"
    #         }
    #     ]
    # }

    # 1、关于arguments的引号转义：注意该引号转义，要生成带转义引号的JSON字符串
    # arguments_string = json.dumps({"city": "Tokyo"})
    # 当这个字符串被放入JSON中时，会自动转义
    # final_json = {
    #     "type": "function_call",
    #     "arguments": arguments_string
    # }
    #
    # print(json.dumps(final_json))
    # 输出：{"type": "function_call", "arguments": "{\"city\": \"Tokyo\"}"}

    # 2、关于output的"Weather(...)"：是用了pydantic，然后str(Weather对象)即可
    # from pydantic import BaseModel
    #
    # class Weather(BaseModel):
    #     city: str
    #     temperature_range: str
    #     conditions: str
    #
    # @function_tool
    # def get_weather(city: str) -> Weather:
    #     """Get the current weather information for a specified city."""
    #     print("[debug] get_weather called")
    #     return Weather(city=city, temperature_range="14-20C", conditions="Sunny with wind.")
    #
    # 在_run_impl.py第621行，SDK调用str(result)将工具返回值转换为字符串：
    # raw_item = ItemHelpers.tool_call_output_item(tool_run.tool_call, str(result))

    # ---------------------------/response格式构建history-------------------------------

    tool_args = None
    tool_name = ''

    message_result = ''
    result_type = ''

    if res.output:
        count = 0
        for item in res.output:
            # print(f'【item{count}】 "{item}"')
            count += 1

        count = 0
        for item in res.output:
            if isinstance(item, ResponseFunctionToolCall):
                # print(f'------------------【item{count}】ResponseFunctionToolCall-------------------')
                # pprint(item.model_dump(), sort_dicts=False, width=120)
                if item.type in ('function_call', 'tool_call'):
                    tool_args = json.loads(item.arguments)
                    tool_name = item.name
                # print(f'-----------------/【item{count}】ResponseFunctionToolCall-------------------')
            elif isinstance(item, ResponseReasoningItem):
                pass
                # print(f'-------------------【item{count}】ResponseReasoningItem---------------------')
                # pprint(item.model_dump(), sort_dicts=False, width=120)
                # print(f'------------------/【item{count}】ResponseReasoningItem---------------------')
            elif isinstance(item, ResponseOutputMessage):
                print(f'-------------------【item{count}】ResponseOutputMessage---------------------')
                pprint(item.model_dump(), sort_dicts=False, width=120)
                message_result = item.content[0].text
                result_type = item.content[0].type
                print(f'------------------/【item{count}】ResponseOutputMessage---------------------')
            else:
                print(f'------------------------【item{count}】other item---------------------------')
                pprint(item.model_dump(), sort_dicts=False, width=120)
                print(f'-----------------------/【item{count}】other item---------------------------')
            count += 1

    def get_weather(city: str, unit: str = 'c') -> dict:
        return {"city": city, "temperature_c": 23, "unit": unit, "status": "sunny"}

    def plan_tool(user_query) -> dict:
        global g_tools_without_plan_str

        http_client = httpx.Client(proxy="http://127.0.0.1:7890")
        p = OpenAI(
            api_key=os.getenv("GROQ_API_KEY") or 'empty',
            base_url='https://api.groq.com/openai/v1',
            http_client=http_client,
        )

        query = f'{g_tools_without_plan_str}\n，以上是可以供你调用的工具情况，请根据用户需求({user_query})，制定具体和优化的调用计划。'
        # print('--------------------------------plan query----------------------------------------')
        # print(query)
        # print('-------------------------------/plan query----------------------------------------')

        res = client.responses.create(
            # model='gpt-oss-20b-mxfp4',
            # model='openai/gpt-oss-20b',
            model='openai/gpt-oss-120b',
            temperature=1.0,
            # temperature=0.6,
            top_p=1.0,
            # top_p=0.95,
            instructions='You are a helpful assistant.',
            input=query,
            stream=False,
            max_output_tokens=8192,
            # reasoning={"effort": 'high'},
            # reasoning={"effort": 'medium'},
            reasoning={"effort": 'low'},
        )
        result = ''
        # print(f'----------------------------------plan结果--------------------------------------------')
        for item in res.output:
            # print(item)
            if isinstance(item, ResponseOutputMessage):
                result = item.content[0].text
        # print(f'---------------------------------/plan结果--------------------------------------------')

        # plan = '根据四则运算的规则，先后调用加减乘除的计算工具。'
        return {"plan_tool的调用结果：": result}
        # return {"plan_tool的调用结果：": plan, "user_query":user_query, "工具描述：": g_tools_without_plan_str}

    def add_tool(a, b) -> dict:
        return {"add_tool的调用结果：": a+b, "输入：": f'{a}, {b}'}

    def sub_tool(a, b) -> dict:
        return {"sub_tool的调用结果：": a-b, "输入：": f'{a}, {b}'}

    def multiple_tool(a, b) -> dict:
        return {"multiple_tool的调用结果：": a*b, "输入：": f'{a}, {b}'}

    def div_tool(a, b) -> dict:
        return {"div_tool的调用结果：": a/b, "输入：": f'{a}, {b}'}

    tool_result = ''
    # print('----------------------tool_name--------------------------')
    # print(tool_name)
    # print(tool_args)
    # print('---------------------/tool_name--------------------------')
    if tool_name:
        # print(f'\n------------------------【调用工具】---------------------------')
        # print(f'调用工具"{tool_name}"，参数为: {tool_args!r}')
        if tool_name == 'get_weather':
            tool_result = get_weather(**tool_args)
            print(tool_result)
        elif tool_name == 'add_tool':
            tool_result = add_tool(**tool_args)
            print(tool_result)
        elif tool_name == 'sub_tool':
            tool_result = sub_tool(**tool_args)
            print(tool_result)
        elif tool_name == 'multiple_tool':
            tool_result = multiple_tool(**tool_args)
            print(tool_result)
        elif tool_name == 'div_tool':
            tool_result = div_tool(**tool_args)
            print(tool_result)
        elif tool_name == 'plan_tool':
            tool_result = plan_tool(**tool_args)
            print(tool_result)
        # print(f'-----------------------/【调用工具】---------------------------')

    if message_result:
        print(f'\n------------------------【输出结果】(type: {result_type})---------------------------')
        print(message_result)
        print(f'-----------------------/【输出结果】---------------------------')

    return '工具调用结果为：' + json.dumps(tool_result) + '\n'
    # return '工具调用结果为：' + json.dumps(tool_result) + '\n' + f'分析结果为：{message_result!r}'

def main_agent_sdk():
    # uv pip install openai-agents
    #
    import asyncio
    from openai import AsyncOpenAI
    from agents import Agent, Runner, function_tool, OpenAIResponsesModel, set_tracing_disabled

    set_tracing_disabled(True)

    @function_tool
    def get_weather(city: str) -> str:
        print(f"[debug] getting weather for {city}")
        return f"The weather in {city} is sunny."

    @function_tool
    def add_tool(a, b) -> dict:
        print(f'add_tool调用了')
        return {"add_tool的调用结果：": a+b, "输入：": f'{a}, {b}'}

    @function_tool
    def sub_tool(a, b) -> dict:
        print(f'sub_tool调用了')
        return {"sub_tool的调用结果：": a-b, "输入：": f'{a}, {b}'}

    @function_tool
    def multiple_tool(a, b) -> dict:
        print(f'multiple_tool调用了')
        return {"multiple_tool的调用结果：": a*b, "输入：": f'{a}, {b}'}

    @function_tool
    def div_tool(a, b) -> dict:
        print(f'div_tool调用了')
        return {"div_tool的调用结果：": a/b, "输入：": f'{a}, {b}'}

    http_client = httpx.AsyncClient(proxies="http://127.0.0.1:7890")
    async def agent_main():
        agent = Agent(
            name="Assistant",
            instructions="You are a helpful assistant.",
            # instructions="You only respond in haikus.",
            model=OpenAIResponsesModel(
                model="openai/gpt-oss-20b",
                # model="openai/gpt-oss-120b",
                openai_client=AsyncOpenAI(
                    api_key=os.getenv("GROQ_API_KEY") or 'empty',
                    base_url='https://api.groq.com/openai/v1',
                    http_client=http_client,
                ),
            ),  # ← 这里需要这个逗号
            # tools=[],
            # tools=[get_weather, add_tool, sub_tool],
            # tools=[add_tool, sub_tool],
            tools=[add_tool, sub_tool, multiple_tool, div_tool],
        )

        result = await Runner.run(agent, "请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算")
        # result = await Runner.run(agent, "请告诉我2356/3567等于多少，保留10位小数，要调用工具计算，不能直接心算")
        # result = await Runner.run(agent, "请告诉我45346+3486*3344-235644/34等于多少，用调用工具计算，不能直接心算")
        # result = await Runner.run(agent, "请告诉我234+45*56-6/7等于多少")
        # result = await Runner.run(agent, "What's the weather in Tokyo?")
        print(result.final_output)  # 如果版本不对，可试试 result.final_output_text

    asyncio.run(agent_main())

async def main_mcp():
    import asyncio, os
    from pathlib import Path
    from agents import Agent
    from agents.run_context import RunContextWrapper
    from agents.mcp import MCPServerStdio

    node_dir = Path.home() / ".nvm/versions/node/v24.6.0"
    node = node_dir / "bin/node"
    server_js = node_dir / "lib/node_modules/@modelcontextprotocol/server-filesystem/dist/index.js"

    # 允许访问的目录：先用当前工作目录，确保一定存在
    allowed_dir = str(Path.cwd())
    print("Using node:", node)
    print("Server js:", server_js)
    print("Allowed dir exists:", os.path.isdir(allowed_dir), allowed_dir)

    # 若你更想指定某个固定目录，可把 allowed_dir 换成那个路径
    async with MCPServerStdio(
        params={
            "command": str(node),
            "args": [str(server_js), allowed_dir],
        },
        cache_tools_list=True,
        name="filesystem",
    ) as server:
        run_context = RunContextWrapper(context=None)
        agent = Agent(name="test", instructions="test")
        # tools = await server.list_tools(run_context, agent)
        # tools = await server.list_tools(run_context=run_context, agent=agent)
        # print("Tools:", [t.name for t in tools])

        tools = await server.list_tools()
        print([t.name for t in tools])

        # 在现有 async with MCPServerStdio(...) as server: 代码块里追加
        # 列目录
        resp = await server.call_tool("list_directory", {"path": "."})
        print("list_directory result:", getattr(resp, "content", None) or getattr(resp, "structured_content", None))

        # 读文本
        resp = await server.call_tool("read_text_file", {"path": "harmony_tool_call.py"})
        print("read_text_file result:", getattr(resp, "content", None) or getattr(resp, "structured_content", None))

    # agent = Agent(
    #     name="Assistant",
    #     instructions="Use the tools to achieve the task",
    #     mcp_servers=[mcp_server_1, mcp_server_2]
    # )

def main_tool_call_agent():
    # llm_simple()
    # res = llm_tool_call()
    # print(res)
    # llm_tool_call(res)
    res = tool_call_agent()
    res = tool_call_agent(last_tool_result=res)
    res = tool_call_agent(last_tool_result=res)
    res = tool_call_agent(last_tool_result=res)
    res = tool_call_agent(last_tool_result=res)
    res = tool_call_agent(last_tool_result=res)
    res = tool_call_agent(last_tool_result=res)
    res = tool_call_agent(last_tool_result=res)
    print('---------------------------res---------------------------------')
    print(res)
    print('--------------------------/res---------------------------------')

if __name__ == "__main__":
    main_tool_call_agent()
    # main_agent_sdk()
    # asyncio.run(main_mcp())



# # 1) 用户输入（Harmony/Responses：input 里放消息，用户文本用 input_text）
# input_msgs = [
#     {
#         "role": "user",
#         "content": [
#             {"type": "input_text", "text": "What's the weather in Berlin right now?"}
#         ],
#     }
# ]

