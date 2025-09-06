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
        temperature=0.6,
        top_p=0.95,
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
def llm_tool_call(last_answer=''):
    print('\n============================================================================================================')
    print('=================================================【started】=================================================')
    print('============================================================================================================\n')

    http_client = httpx.Client(proxy="http://127.0.0.1:7890")

    # client = OpenAI(
    #     api_key='empty',
    #     base_url='http://powerai.cc:18002/v1',
    # )

    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY") or 'empty',
        base_url='https://api.groq.com/openai/v1',
        http_client=http_client,
        # http_client=openai.DefaultHttpxClient(verify=False),  # 用于自建的vllm openai api的ssl访问(https访问)， # 阿里云购买了正式证书（可以是免费的）后，即可开启verify，也就是去掉本行
    )
    query = '<总体要求>\n你的角色：你是智能化系统的流程控制和优化专家。\n你的任务：必须回答【用户问题】，而且系统已经为你准备了【工具集】，你可以调用其中的工具，但要严格根据【工具描述】访问合适的工具。\n你的回复要求：严格根据【回复流程及格式要求】进行回复，要注意，整个回复流程是一个规划和行动迭代的过程，具体包括：\n    1）规划：你根据【用户问题】，且一定要注意【用户经验】的重要性，给出总体解决思路和工具调用规划。\n    2）迭代过程：\n        a）工具调用申请：你根据规划，给出一个工具调用申请（包括工具的具体输入参数）；\n        b）观察(返回工具调用结果)：这一步由系统根据你的工具调用申请，强制执行对应工具，并返回工具调用结果；\n        c）工具调用结果分析：你要严格根据系统返回的工具调用结果，对你之前的工具调用申请参数、甚至规划进行分析和调整；\n        d）最终答复：仅当你觉得返回的结果已经解决【用户问题】时，需要给出【最终答复】\n</总体要求>\n\n<工具集>\n工具名称: Folder_Tool\n工具描述: 返回指定文件夹下所有文件和文件夹的名字信息。\n\n工具参数: [\n\t{\t参数名称: dir,\n\t\t参数类型: string,\n\t\t参数描述: \n本参数为文件夹所在的路径\n,\n\t\t参数是否必需: True,\n\t},\n]\n\n\n</工具集>\n\n<回复流程及格式要求>\n[规划]这里写你关于【用户问题】的总体解决思路和工具调用规划，要调理清晰、逻辑精确。\n\n[工具调用申请]这里你写:\n{\n    \'tool_invoke\':\'no\'或者\'yes\',\n    \'tool_name\':你所要调用的工具的名称,    (注意工具名称必须是这些名称之一 [\'Folder_Tool\'] 。)\n    \'tool_parameters\':{\n        \'para1\' : value1,\n        \'para2\' : value2,   （注意：如果\'value\'值为代码字符串，则代码字符串起始必须换一行顶格，绝对不能有额外缩进。）\n        ... , \n    },\n}\n\n[观察]这里不能由你写，系统会自动在这里写入工具调用结果信息。\n\n###... (这个 思考/工具调用/工具调用的输入/观察 的流程，可以被重复0次或多次，只要你觉得可以给出最终答复，就要结束这个流程，防止不断循环。)\n\n[工具调用结果分析]这里写你的分析和可能的调整，调理一定要清晰。\n\n[最终答复]只有问题已经解决，你才能写这个最终答复，调理一定要清晰。\n\n</回复流程及格式要求>\n\n<用户问题>\n我叫土土，请告诉我"file_to_find.txt"在"/home/tutu/demo/"文件夹的哪个具体文件夹中，要仔细搜索其子文件夹。\n</用户问题>\n\n<用户经验>\n\n</用户经验>\n\n现在你开始回复：\n'


    tools = [
        # {"type": "python", "container": {"type": "auto"}},
        # {"type": "code_interpreter", "container": {"type": "auto"}},
        {
            "type": "function",
            "name": "get_weather",
            "description": "Get current weather in a given city",
            "strict": True,  # 让模型严格遵循 JSON Schema
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "unit": {"type": "string", "description": "temperature unit", "enum": ["c", "f"]},
                },
                "required": ["city"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "Folder_Tool",
            "description": "获取当前目录下的子文件夹清单和文件清单",
            "strict": True,  # 让模型严格遵循 JSON Schema
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件夹的路径"},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        }
    ]
    tools = [
        # {"type": "python", "container": {"type": "auto"}},
        # {"type": "code_interpreter", "container": {"type": "auto"}},
        {
            "type": "function",
            "name": "get_weather",
            "description": "Get current weather in a given city",
            "strict": True,  # 让模型严格遵循 JSON Schema
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "unit": {"type": "string", "description": "temperature unit", "enum": ["c", "f"]},
                },
                "required": ["city"],
                "additionalProperties": False,
            },
        },
        Folder_Tool.get_tool_param_dict(),
        # {
        #     "type": "function",
        #     "name": "Folder_Tool",
        #     "description": "获取当前目录下的子文件夹清单和文件清单",
        #     "strict": True,  # 让模型严格遵循 JSON Schema
        #     "parameters": {
        #         "type": "object",
        #         "properties": {
        #             "path": {"type": "string", "description": "文件夹的路径"},
        #         },
        #         "required": ["path"],
        #         "additionalProperties": False,
        #     },
        # }
    ]

    # input='我叫土土，帮我写一首简短的爱情诗'
    input = '告诉我杭州天气如何，并且告诉我"file_to_find.txt"在"/home/tutu/demo/"文件夹的哪个具体文件夹中'
    # input='请告诉我"file_to_find.txt"在"/home/tutu/demo/"文件夹的哪个具体文件夹中，并且告诉我1+1=？'
    # input='告诉我1+1=？'
    # input='今天杭州天气如何？'
    # input='Multiply 64548*15151 using builtin python interpreter.'
    # input='计算一下1234/4567等于多少，保留10位小数'
    # input = query

    input = last_answer + '\n' + input
    print('---------------------input--------------------')
    print(input)
    print('--------------------/input--------------------\n')

    res = client.responses.create(
        # model='gpt-oss-20b-mxfp4',
        # model='openai/gpt-oss-20b',
        model='openai/gpt-oss-120b',
        temperature=0.6,
        top_p=0.95,
        instructions='You are a helpful assistant.',
        input=input,

        tools=tools,
        tool_choice="auto",
        parallel_tool_calls=False,
        stream=False,

        max_output_tokens=8192,
        reasoning={"effort": 'low'},
    )

    thinking_started = False
    result_started = False
    tool_args = None
    tool_name = ''

    message_result = ''
    result_type = ''

    if res.output:
        count = 0
        for item in res.output:
            print(f'【item{count}】 "{item}"')
            count += 1

        count = 0
        for item in res.output:
            if isinstance(item, ResponseFunctionToolCall):
                print(f'------------------【item{count}】ResponseFunctionToolCall-------------------')
                pprint(item.model_dump(), sort_dicts=False, width=120)
                if item.type in ('function_call', 'tool_call'):
                    tool_args = json.loads(item.arguments)
                    tool_name = item.name
                print(f'-----------------/【item{count}】ResponseFunctionToolCall-------------------')
            elif isinstance(item, ResponseReasoningItem):
                print(f'-------------------【item{count}】ResponseReasoningItem---------------------')
                pprint(item.model_dump(), sort_dicts=False, width=120)
                print(f'------------------/【item{count}】ResponseReasoningItem---------------------')
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
        # 这里替换为真实实现
        return {"city": city, "temperature_c": 23, "unit": unit, "status": "sunny"}

    tool_result = ''
    if tool_args:
        print(f'\n------------------------【调用工具】---------------------------')
        print(f'调用工具"{tool_name}"，参数为: {tool_args!r}')
        if tool_name == 'get_weather':
            tool_result = get_weather(**tool_args)
            print(tool_result)
        print(f'-----------------------/【调用工具】---------------------------')

    if message_result:
        print(f'\n------------------------【输出结果】(type: {result_type})---------------------------')
        print(message_result)
        print(f'-----------------------/【输出结果】---------------------------')

    return '工具调用结果为：' + json.dumps(tool_result) + '\n' + f'分析结果为：{message_result!r}'


if __name__ == "__main__":
    # llm_simple()
    res = llm_tool_call()
    print(res)
    llm_tool_call(res)

# # 1) 用户输入（Harmony/Responses：input 里放消息，用户文本用 input_text）
# input_msgs = [
#     {
#         "role": "user",
#         "content": [
#             {"type": "input_text", "text": "What's the weather in Berlin right now?"}
#         ],
#     }
# ]

