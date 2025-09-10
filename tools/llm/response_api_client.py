from openai import OpenAI, APIError
from openai.types.responses import Response, ResponseReasoningItem, ResponseFunctionToolCall, ResponseOutputMessage
from openai.types.responses import ToolParam, FunctionToolParam

from typing import List, Dict, Any, Type, Literal, Optional, Callable
from pydantic import BaseModel, Field, ConfigDict

import json
from pprint import pprint

import llm_protocol
from llm_protocol import LLM_Config
import config
from config import dred, dgreen, dblue, dyellow, dcyan

DEBUG = True
# DEBUG = False

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def dpprint(*args, **kwargs):
    if DEBUG:
        pprint(*args, **kwargs)

# ---------------------------------pydantic导出示例---------------------------------
# class M(BaseModel):
#     # 必填：必须出现
#     a: int
#
#     # 必填但可为 None：必须出现，但能是 null
#     b: Optional[int]  # 或 int | None
#
#     # ---------可省略：不出现也行；出现时可为 None--------，后续用m.model_dump(exclude_unset=True)即可
#     c: Optional[int] = None
#
#     # 可省略：不出现也行；出现时必须是 int
#     d: int | None = Field(default=None)  # 出现且为 None 也允许

# m = M(a=1, b=None)  # c、d 未提供
# m.model_dump(exclude_unset=True)
# # -> 只包含 a、b
#
# m.model_dump(exclude_none=True)
# # -> 过滤掉 None 值的字段（此时 b 会被去掉）
#
# m.model_dump(exclude_unset=True, exclude_none=True)
# # -> 只留 a（因为 b 是 None 被过滤，c/d 未提供被过滤）
# --------------------------------/pydantic导出示例---------------------------------

# --------------------------------tool参数示例---------------------------------
# {
#     "type": "function",
#     "name": "add_tool",
#     "description": "计算两个数的和",
#     "strict": True,  # 让模型严格遵循 JSON Schema
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "a": {"type": "number", "description": "a"},
#             "b": {"type": "number", "description": "b"},
#         },
#         "required": [],
#         "additionalProperties": False,
#     },
# },
# -------------------------------/tool参数示例---------------------------------

Property_Type = Literal["integer", "number", "boolean", "string"]

class Tool_Property(BaseModel):
    type            :Property_Type              # 如"integer", "number", "boolean", "string"
    description     :str                        # 如"加数"、"被加数"
    enum            :Optional[List[str]] = None # 如属性unit的可选值：["c", "f"]

class Tool_Parameters(BaseModel):
    type            :str = 'object'
    properties      :Dict[str, Tool_Property]          # 如{ 'a': {}, 'b': {} }
    required        :List[str] = Field(default_factory=list)    # 如['a', 'b']
    additionalProperties :bool = False

class Tool_Request(BaseModel):
    type            :str = 'function'
    name            :str    # 如'add_tool'
    description     :str    # 如'计算两个数的和'
    strict          :bool = True
    parameters      :Tool_Parameters

    # 所调用的函数
    # 仅在本地使用，不参与 JSON 序列化
    func        : Optional[Callable] = Field(default=None, exclude=True, repr=False)

    # 允许 pydantic 接受 Callable 等任意类型（否则有些版本会抱怨）
    model_config = ConfigDict(arbitrary_types_allowed=True)
# --------------------------------response请求参数示例---------------------------------
# res = client.responses.create(
#     model='openai/gpt-oss-20b',
#     temperature=1.0,
#     top_p=1.0,
#     instructions='You are a helpful assistant.',
#     input=PROMPT_TOOL_CALL,
#
#     tools=tools,
#     tool_choice="auto",
#     parallel_tool_calls=False,
#     stream=False,
#
#     max_output_tokens=8192,
#     reasoning={"effort": 'low'},
# )
# -------------------------------/response请求参数示例---------------------------------

# --------------------------------input示例---------------------------------
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
# -------------------------------/input示例---------------------------------

class Response_Request(BaseModel):
    model           :str
    temperature     :float = 1.0
    top_p           :float = 1.0
    instructions    :str =  'You are a helpful agent.'  # 注意这里用了'agent'
    input           :str | List[Dict[str, Any]] = None  # 非第一次responses.create时为None，并在Response_LLM_Client里采用history_input_list
    tools           :List[Tool_Request]
    previous_response_id    :Optional[str] = None    # 上一次openai.response.create()返回的res.id
    tool_choice     :str = 'auto'
    parallel_tool_calls :bool = False
    stream          :bool = False
    max_output_tokens   :int = 8192
    reasoning       :Dict = Field(default_factory=lambda: {"effort": 'low'})

class Response_Result(BaseModel):
    # 返回内容
    reasoning               :str = ''
    output                  :str = ''
    function_tool_call      :Dict[str, Any] = None # {'arguments': '{"a":2356,"b":3567,"unit":"meter"}', 'call_id': 'fc_cfaf81b5-7aec-457f-b745-59b8aee69648', 'name': 'div_tool'}
    other_item              :Any = None

    # 工具调用结果
    previous_response_id    :str = None    # 上一次openai.response.create()返回的res.id
    tool_call_result        :str = ''

    error                   :str = ''

class Response_LLM_Client:
    def __init__(self, llm_config:LLM_Config):
    # def __init__(self, client: OpenAI):
        self.llm_config = llm_config
        self.openai = None
        self.funcs = []                 # [{'name':'...', 'func':func}]

        # input_list相关
        self.history_input_list = None  # 历史input_list(用于多轮的tool call)

    # 将Response_LLM_Client当作agent用(用tool call)
    def init(self):
        if self.llm_config.vpn_on:
            import httpx
            http_client = httpx.Client(proxy=config.g_vpn_proxy)
            self.openai = OpenAI(
                api_key=self.llm_config.api_key,
                base_url=self.llm_config.base_url,
                http_client=http_client,
            )
        else:
            self.openai = OpenAI(
                api_key=self.llm_config.api_key,
                base_url=self.llm_config.base_url,
            )

    # 将Response_LLM_Client当作agent用(用tool call)
    # ---------------存在问题---------------
    # agent_run()不宜放在life-agent.tools.llm.Response_LLM_Client里，而应在life-agent.agent.core里
    def legacy_agent_run(self, query, tools) -> str:
        response_request = Response_Request(
            model=self.llm_config.llm_model_id,
            input=query,
            tools=tools,
        )

        responses_result = self.responses_create(request=response_request)

        while not hasattr(responses_result, 'output') or responses_result.output=='' :
            response_request = Response_Request(
                instructions=query,  # 这里仍然是'请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'
                # instructions='继续调用工具直到完成user的任务',
                model=self.llm_config.llm_model_id,
                tools=tools,
            )
            responses_result = self.responses_create(request=response_request)

            if responses_result.output != '':
                dprint('-----------------------------------最终结果---------------------------------------------')
                dprint(responses_result.output)
                dprint('-----------------------------------最终结果---------------------------------------------')
                dgreen('-----------------------------------最终结果---------------------------------------------')
                dgreen(responses_result.output)
                dgreen('-----------------------------------最终结果---------------------------------------------')
                break

        return responses_result.output

    def history_input_add_tool_call_result_item(self, call_id, output, error):
        tool_call_result_item = {
            "type": "function_call_output",
            "call_id": call_id,
            "output": output,
            "error": error
        }
        self.history_input_list.append(tool_call_result_item)

    def history_input_add_output_item(self, output):
        output_item = {
            "role": "assistant",
            "content": output,
        }
        # output_item = {
        #     "type": "message",
        #     "role": "assistant",
        #     "content": [{"type": "input_text", "text": output}],
        # }
        self.history_input_list.append(output_item)

    # agent在一轮run结束后，需要将input_list中的ResponseReasoningItem、ResponseFunctionToolCall和ResponseOutputMessage等清除
    # 否则agent第二轮run时，server会报validation errors for ValidatorIterator之类的错误
    def history_input_clear_after_this_run(self):
        # dyellow(f'history input before: {self.history_input_list}')
        self.history_input_list[:] = [
            item for item in self.history_input_list
            if isinstance(item, dict) and ('type'in item and item['type'] =='message' or 'role' in item)
        ]
        # dyellow(f'history input after: {self.history_input_list}')

    def responses_create(self, request:Response_Request, new_run)->Response_Result:
        # 第一次responses.create
        if self.history_input_list is None:
            self.history_input_list = [
                {
                    "role": "user",
                    "content": request.instructions,
                }
            ]
            # self.history_input_list = [
            #     {
            #         "type": "message",
            #         "role": "user",
            #         # "content": request.input,
            #         "content": [{"type": "input_text", "text": request.instructions}],
            #     }
            # ]
        else:
            if new_run:
                self.history_input_list += [
                    {
                        "role": "user",
                        "content": request.instructions,
                    }
                ]
                # self.history_input_list += [
                #     {
                #         "type": "message",
                #         "role": "user",
                #         # "content": request.input,
                #         "content": [{"type": "input_text", "text": request.instructions}],
                #     }
                # ]



        dyellow('===================================request.instructions====================================')
        dyellow(request.instructions)
        dyellow('==================================/request.instructions====================================')

        dblue('=================================self.history_input_list===================================')
        for item in self.history_input_list:
            dblue(item)
        dblue('================================/self.history_input_list===================================')

        res = None
        response_result = None
        try:
            res = self.openai.responses.create(input=self.history_input_list, **request.model_dump(exclude_none=True))
        except Exception as e:
            dred(e)

        # 不管responses_create是否为第一次，按照官方要求，添加responses.create()的response.output(后续需要在tool调用成功后，在history_input_list末尾添加{"type": "function_call_output", ...})
        if res:
            self.history_input_list += res.output
            response_result = self._responses_result(res)
        else:
            dred(f'【Response_LLM_Client.responses_create】Warning: responses.create()返回失败.')


        # ----------------------注册tool func-------------------------
        self.funcs = [] # 要先清除之前的tools
        for tool in request.tools:
            # dred(tool)
            func_dict = {
                'name' : tool.name,
                'func' : tool.func,
            }
            self.funcs.append(func_dict)
        # ---------------------/注册tool func-------------------------

        # 调用tool
        # response_result = self.call_tool(response_result)

        return response_result

    def _responses_result(self, res:Response):
        # dprint(res)
        # dprint('------------------------------Response---------------------------------------')
        # dpprint(res.model_dump())
        # dprint('-----------------------------/Response---------------------------------------')

        response_result = Response_Result(previous_response_id = res.id)

        dprint()
        dprint(f'==========================================Response Items(res id: "{res.id}")==========================================')
        if res.output:
            for item in res.output:
                if isinstance(item, ResponseFunctionToolCall):
                    dprint('---------------------------ResponseFunctionToolCall------------------------------------')
                    dprint(item)
                    dprint('--------------------------/ResponseFunctionToolCall------------------------------------')
                    dprint()
                    # {'arguments': '{"a":22,"b":33}', 'call_id': 'fc_6b305c5f-2fc6-4a5b-9559-b909da57de2f', 'name': 'mul_tool'}
                    response_result.function_tool_call = item.model_dump(exclude={'id', 'status', 'type'})
                elif isinstance(item, ResponseReasoningItem):
                    dprint('-----------------------------ResponseReasoningItem-------------------------------------')
                    dprint(item)
                    dprint('----------------------------/ResponseReasoningItem-------------------------------------')

                    dblue('-----------------------------ResponseReasoningItem-------------------------------------')
                    dblue(item)
                    if hasattr(item, "content") and item.content and 'text' in item.content[0]:
                        dblue(item.content[0]['text'])
                    dblue('----------------------------/ResponseReasoningItem-------------------------------------')

                    dprint()
                    if hasattr(item, "content") and item.content and 'text' in item.content[0]:
                        response_result.reasoning = item.content[0]['text']
                elif isinstance(item, ResponseOutputMessage):
                    dprint('-----------------------------ResponseOutputMessage-------------------------------------')
                    dprint(item)
                    dprint('----------------------------/ResponseOutputMessage-------------------------------------')
                    dprint()
                    if item.content and item.content[0].text:
                        response_result.output = item.content[0].text
                else:
                    dprint('----------------------------------other item-------------------------------------------')
                    dprint(item)
                    dprint('---------------------------------/other item-------------------------------------------')
                    dprint()
                    response_result.other_item = item
        dprint('=========================================/Response Items==========================================')

        dprint()
        dprint('---------------------------------response_result(未调用工具)------------------------------------')
        dpprint(response_result.model_dump())
        dprint('--------------------------------/response_result(未调用工具)------------------------------------')

        return response_result

    # -------------------存在问题-------------------
    # call_tool()不宜放在life-agent.tools.llm.Response_LLM_Client里，而应在life-agent.agent.core的Response_API_Tool_Agent里
    # def legacy_call_tool(self, response_result:Response_Result)->Response_Result:
    #     tool_call = response_result.function_tool_call
    #     if tool_call and 'name' in tool_call:
    #         tool_name = tool_call['name']
    #         dprint(f'tool_name = "{tool_name}"')
    #
    #         for func in self.funcs:
    #             if tool_name == func['name']:
    #                 dprint('----------tool_call-------------')
    #                 dprint(tool_call)
    #                 args = json.loads(tool_call['arguments'])
    #                 dprint(f'args: {args!r}')
    #                 dprint('---------/tool_call-------------')
    #
    #                 # ------------------调用tool------------------
    #                 func_rtn = func['func'](**args)
    #                 # -----------------/调用tool------------------
    #
    #                 response_result.tool_call_result = json.dumps(func_rtn, ensure_ascii=False)
    #                 # history_input_list末尾添加tool调用结果
    #
    #                 dprint('----------history_input_list.append(tool_call_result_item)-------------')
    #                 # dprint(tool_call)
    #                 # dprint(response_result.tool_call_result)
    #                 if response_result.error:
    #                     tool_call_result_item = {
    #                         "type": "function_call_output",
    #                         "call_id": tool_call['call_id'],
    #                         "output": json.dumps({tool_call['name']: response_result.tool_call_result}),
    #                         "error": response_result.error,
    #                         # "output": {tool_call['name']: response_result.tool_call_result}
    #                     }
    #                 else:
    #                     tool_call_result_item = {
    #                         "type": "function_call_output",
    #                         "call_id": tool_call['call_id'],
    #                         "output": json.dumps({tool_call['name']: response_result.tool_call_result})
    #                         # "output": {tool_call['name']: response_result.tool_call_result}
    #                     }
    #
    #                 dprint(tool_call_result_item)
    #                 dprint('---------/history_input_list.append(tool_call_result_item)-------------')
    #                 self.history_input_list.append(tool_call_result_item)
    #
    #                 dprint('-----------------responses_result(工具调用后)-----------------')
    #                 dpprint(response_result.model_dump())
    #                 dprint('----------------/responses_result(工具调用后)-----------------')
    #
    #                 dgreen('-----------------responses_result(工具调用后)-----------------\n{')
    #                 for k,v in response_result.model_dump().items():
    #                     dgreen(f'\t {k!r}:{v!r}')
    #                 dgreen('}\n----------------/responses_result(工具调用后)-----------------')
    #                 return response_result
    #     return response_result

def main_response_request_pprint():
    input = '你是谁？'
    add_tool = Tool_Request(
        name='add_tool',
        description='加法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='加数'),
                'b': Tool_Property(type='number', description='被加数'),
                'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
    )
    tools = [
        add_tool,
    ]
    response_request = Response_Request(
        model='openai/gpt-oss-20b',
        input=input,
        tools=tools,
    )

    dpprint(response_request.model_dump())

def main_response_llm_client():
    add_tool = Tool_Request(
        name='add_tool',
        description='加法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='加数'),
                'b': Tool_Property(type='number', description='被加数'),
                # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
        func=lambda a, b: {"result": a + b}
        # func=lambda a, b, unit: {"result": a + b, "unit": unit}
    )
    sub_tool = Tool_Request(
        name='sub_tool',
        description='减法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='减数'),
                'b': Tool_Property(type='number', description='被减数'),
                # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
        func=lambda a, b: {"result": a - b}
        # func=lambda a, b, unit: {"result": a - b, "unit": unit}
    )
    mul_tool = Tool_Request(
        name='mul_tool',
        description='乘法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='乘数'),
                'b': Tool_Property(type='number', description='被乘数'),
                # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
        func=lambda a, b: {"result": a * b}
        # func=lambda a, b, unit: {"result": a * b, "unit": unit}
    )
    div_tool = Tool_Request(
        name='div_tool',
        description='除法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='除数'),
                'b': Tool_Property(type='number', description='被除数'),
                # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
        func=lambda a, b: {"result": a / b}
        # func=lambda a, b, unit: {"result": a / b, "unit": unit}
    )

    # from agent.tools.folder_tool import Folder_Tool
    # fold_tool = Folder_Tool.get_tool_param_dict()

    # tools = []
    # tools = [div_tool]
    tools = [add_tool, sub_tool, mul_tool, div_tool]

    # -------------打印输入参数--------------
    # dpprint(response_request.model_dump())

    client = Response_LLM_Client(llm_config=llm_protocol.g_online_groq_gpt_oss_20b)
    client.init()

    query = '请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'
    response_request = Response_Request(
        model=client.llm_config.llm_model_id,
        input=query,
        tools=tools,
    )
    responses_result = client.responses_create(request=response_request)
    responses_result = client.legacy_call_tool(responses_result)

    dprint(f'responses_result.output: {responses_result.output!r}')
    # dprint(f'responses_result.function_tool_call: {responses_result.function_tool_call}')

    while not hasattr(responses_result, 'output') or responses_result.output=='' :
        response_request = Response_Request(
            instructions=query, # 这里仍然是'请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'
            # instructions='继续调用工具直到完成user的任务',
            model=client.llm_config.llm_model_id,
            tools=tools,
        )
        responses_result = client.responses_create(request=response_request)
        responses_result = client.legacy_call_tool(responses_result)
        dprint(f'responses_result: {responses_result!r}')

        if responses_result.output != '':
            dprint('-----------------------------------最终结果---------------------------------------------')
            dprint(responses_result.output)
            dprint('-----------------------------------最终结果---------------------------------------------')
            dgreen('-----------------------------------最终结果---------------------------------------------')
            dgreen(responses_result.output)
            dgreen('-----------------------------------最终结果---------------------------------------------')
            break

def main_response_agent():
    add_tool = Tool_Request(
        name='add_tool',
        description='加法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='加数'),
                'b': Tool_Property(type='number', description='被加数'),
                # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
        func=lambda a, b: {"result": a + b}
        # func=lambda a, b, unit: {"result": a + b, "unit": unit}
    )
    sub_tool = Tool_Request(
        name='sub_tool',
        description='减法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='减数'),
                'b': Tool_Property(type='number', description='被减数'),
                # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
        func=lambda a, b: {"result": a - b}
        # func=lambda a, b, unit: {"result": a - b, "unit": unit}
    )
    mul_tool = Tool_Request(
        name='mul_tool',
        description='乘法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='乘数'),
                'b': Tool_Property(type='number', description='被乘数'),
                # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
        func=lambda a, b: {"result": a * b}
        # func=lambda a, b, unit: {"result": a * b, "unit": unit}
    )
    div_tool = Tool_Request(
        name='div_tool',
        description='除法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='除数'),
                'b': Tool_Property(type='number', description='被除数'),
                # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
        func=lambda a, b: {"result": a / b}
        # func=lambda a, b, unit: {"result": a / b, "unit": unit}
    )

    # from agent.tools.folder_tool import Folder_Tool
    # fold_tool = Folder_Tool.get_tool_param_dict()

    tools = [add_tool, sub_tool, mul_tool, div_tool]

    # -------------打印输入参数--------------
    # dpprint(response_request.model_dump())

    query = '请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'

    client = Response_LLM_Client(llm_config=llm_protocol.g_online_groq_gpt_oss_20b)
    client.init()
    client.legacy_agent_run(query=query, tools=tools)

if __name__ == "__main__":
    # main_response_request_pprint()
    # main_response_llm_client(model='openai/gpt-oss-120b')
    main_response_llm_client()
    # main_response_agent()