from openai import OpenAI, APIError
from openai.types.responses import Response, ResponseReasoningItem, ResponseFunctionToolCall, ResponseOutputMessage
from openai.types.responses import ToolParam, FunctionToolParam

from typing import List, Dict, Any, Type, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

from pprint import pprint

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
    input           :str | List[Dict[str, Any]]
    tools           :List[Tool_Request]
    tool_choice     :str = 'auto'
    parallel_tool_calls :bool = False
    stream          :bool = False
    max_output_tokens   :int = 8192
    reasoning       :Dict = Field(default_factory=lambda: {"effort": 'low'})

class Response_Result(BaseModel):
    reasoning   :str = ''
    output      :str = ''
    function_tool_call   :ResponseFunctionToolCall = None # {'tool_name':'...', 'tool_args','...'}
    other_item  :Any = None

class Response_LLM_Client:
    def __init__(self, client: OpenAI):
        self.client = client

    def responses_create(self, request:Response_Request):
        res = self.client.responses.create(**request.model_dump(exclude_none=True))
        return res

    def responses_result(self, res:Response):
        # dprint(res)
        dprint('------------------------------Response---------------------------------------')
        dpprint(res.model_dump())
        dprint('-----------------------------/Response---------------------------------------')

        response_result = Response_Result()

        dprint()
        dprint('==========================================Response Items==========================================')
        if res.output:
            for item in res.output:
                if isinstance(item, ResponseFunctionToolCall):
                    dprint('---------------------------ResponseFunctionToolCall------------------------------------')
                    dprint(item)
                    dprint('--------------------------/ResponseFunctionToolCall------------------------------------')
                    dprint()
                    response_result.function_tool_call = item
                elif isinstance(item, ResponseReasoningItem):
                    dprint('-----------------------------ResponseReasoningItem-------------------------------------')
                    dprint(item)
                    dprint('----------------------------/ResponseReasoningItem-------------------------------------')
                    dprint()
                    if item.content and 'text' in item.content[0]:
                        response_result.reasoning = item.content[0]['text']
                elif isinstance(item, ResponseOutputMessage):
                    dprint('-----------------------------ResponseOutputMessage-------------------------------------')
                    dprint(item)
                    dprint('----------------------------/ResponseOutputMessage-------------------------------------')
                    dprint()
                    if item.content and 'text' in item.content[0]:
                        response_result.output = item.content[0]['text']
                else:
                    dprint('----------------------------------other item-------------------------------------------')
                    dprint(item)
                    dprint('---------------------------------/other item-------------------------------------------')
                    dprint()
                    response_result.other_item = item
        dprint('=========================================/Response Items==========================================')
        return response_result

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
                'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
    )
    sub_tool = Tool_Request(
        name='sub_tool',
        description='减法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='减数'),
                'b': Tool_Property(type='number', description='被减数'),
                'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
    )
    mul_tool = Tool_Request(
        name='mul_tool',
        description='乘法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='乘数'),
                'b': Tool_Property(type='number', description='被乘数'),
                'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
    )
    div_tool = Tool_Request(
        name='div_tool',
        description='除法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='除数'),
                'b': Tool_Property(type='number', description='被除数'),
                'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
    )
    # tools = []
    # tools = [div_tool]
    tools = [add_tool, sub_tool, mul_tool, div_tool]

    input = '请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'
    # input = '你是谁？'
    response_request = Response_Request(
        model='openai/gpt-oss-20b',
        input=input,
        tools=tools,
    )

    # -------------打印输入参数--------------
    # dpprint(response_request.model_dump())

    import httpx, os, json
    http_client = httpx.Client(proxy="http://127.0.0.1:7890")
    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY") or 'empty',
        base_url='https://api.groq.com/openai/v1',
        http_client=http_client,
    )
    client = Response_LLM_Client(client=client)
    res = client.responses_create(request=response_request)
    responses_result = client.responses_result(res=res)

    dprint()
    dprint('---------------------------------response result------------------------------------')
    dpprint(responses_result.model_dump())
    dprint('--------------------------------/response result------------------------------------')


if __name__ == "__main__":
    # main_response_request_pprint()
    main_response_llm_client()