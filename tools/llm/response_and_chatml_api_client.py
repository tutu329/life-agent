from openai import OpenAI, APIError
from openai.types.responses import Response, ResponseReasoningItem, ResponseFunctionToolCall, ResponseOutputMessage, ResponseCompletedEvent
from openai.types.responses import ToolParam, FunctionToolParam

from typing import List, Dict, Any, Type, Literal, Optional, Callable
from pydantic import BaseModel, Field, ConfigDict

import json
from pprint import pprint

from agent.tools.protocol import Tool_Request
import llm_protocol
from llm_protocol import LLM_Config
import config
from config import dred, dgreen, dblue, dyellow, dcyan
from console import err

from copy import deepcopy

DEBUG = config.Global.app_debug

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def dpprint(*args, **kwargs):
    if DEBUG:
        pprint(*args, **kwargs)

class LLM_Status(BaseModel):
    canceling           :bool = False   # agent的query是否正在canceling
    canceled            :bool = False   # agent的query是否canceled

class Response_Request(BaseModel):
    model           :str
    temperature     :float = 1.0
    top_p           :float = 1.0
    instructions    :str =  'You are a helpful agent.'
    # instructions    :str =  'You are a helpful agent. if tool has no arguments, use "{}", do not use "{'', ''}" or "{\"\", \"\"}".'  # 注意这里用了'agent'
    # input           :str | List[Dict[str, Any]] = None  # 非第一次responses.create时为None，并在Response_LLM_Client里采用history_input_list
    tools           :Optional[List[Tool_Request]] = None
    previous_response_id    :Optional[str] = None    # 上一次openai.response.create()返回的res.id
    tool_choice     :str = 'auto'
    parallel_tool_calls :bool = False
    stream          :bool = False
    max_output_tokens   :int = 8192
    reasoning       :Dict = Field(default_factory=lambda: {"effort": 'low'})

    model_config = ConfigDict(extra='allow')

class Response_Result(BaseModel):
    # 返回内容
    reasoning               :Optional[str] = None
    output                  :Optional[str] = None
    function_tool_call      :Dict[str, Any] = None # {'arguments': '{"a":2356,"b":3567,"unit":"meter"}', 'call_id': 'fc_cfaf81b5-7aec-457f-b745-59b8aee69648', 'name': 'div_tool'}
    other_item              :Any = None

    # 工具调用结果
    previous_response_id    :str = None    # 上一次openai.response.create()返回的res.id
    tool_call_result        :str = ''

    error                   :str = ''

    # 用于放置agent as tool的tool调用结果
    agent_as_tool_call_result   :str = ''

class Response_and_Chatml_LLM_Client:
    def __init__(self, llm_config:LLM_Config):
    # def __init__(self, client: OpenAI):
        self.llm_config = llm_config
        self.openai = None

        # 必须将Response_and_Chatml_LLM_Client中的self.funcs替换为Toolcall_Agent中的tool_funcs_dict来管理
        # self.funcs = []                 # [{'name':'...', 'func':func}]

        # input_list相关
        self.history_input_list = None  # 历史input_list(用于多轮的tool call)

        # stream的数据

        self.current_chunk = ''
        self.reasoning_text = ''
        self.output_text = ''

        self.response_output = []       # stream完成后的：可以作为history的output
        self.function_tool_call = {}    # stream完成后的：function_tool_call如{'arguments': '{"a":22,"b":33}', 'call_id': 'fc_250d570d-15ca-4619-a27b-0ee9b008063b', 'name': 'mul_tool'}
        self.tool_arguments = ''        # stream完成后的：tool_arguments如{"a":22,"b":33}
        self.tool_call_id = ''          # stream完成后的：tool_call_id
        self.tool_name = ''             # stream完成后的：tool_name

        self.status:LLM_Status = LLM_Status()

    def set_cancel(self):
        # print('-----------llm canceling...-------------')
        self.status.canceling = True

    def unset_cancel(self):
        # print('-----------llm canceling...-------------')
        self.status.canceling = False

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
    # def legacy_agent_run(self, query, tools) -> str:
    #     response_request = Response_Request(
    #         model=self.llm_config.llm_model_id,
    #         input=query,
    #         tools=tools,
    #     )
    #
    #     responses_result = self.responses_create(request=response_request)
    #
    #     while not hasattr(responses_result, 'output') or responses_result.output=='' :
    #         response_request = Response_Request(
    #             instructions=query,  # 这里仍然是'请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'
    #             # instructions='继续调用工具直到完成user的任务',
    #             model=self.llm_config.llm_model_id,
    #             tools=tools,
    #         )
    #         responses_result = self.responses_create(request=response_request)
    #
    #         if responses_result.output != '':
    #             dprint('-----------------------------------最终结果---------------------------------------------')
    #             dprint(responses_result.output)
    #             dprint('-----------------------------------最终结果---------------------------------------------')
    #             dgreen('-----------------------------------最终结果---------------------------------------------')
    #             dgreen(responses_result.output)
    #             dgreen('-----------------------------------最终结果---------------------------------------------')
    #             break
    #
    #     return responses_result.output

    def history_input_add_tool_call_result_item(self, arguments, call_id, output, error):
        if not self.llm_config.chatml:
            # response接口
            tool_call_result_item = {
                "type": "function_call_output",
                "call_id": call_id,
                # 'arguments': arguments,   # ------官方没有要求输出该参数，增加该参数输出后，似乎并没有影响tool call全流程的推理精度------
                "output": output,
                "error": error
            }
        else:
            # chatml接口
            tool_call_result_item = {
                "role": "tool",
                "tool_call_id": call_id,
                "content": f'tool call result: "{output}", tool call error: "{error}".',
                # "content": f'tool call arguments: "{arguments}", tool call result: "{output}", tool call error: "{error}".',
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
    def history_input_reduce_content_after_this_run(self):
        # dyellow(f'history input before: {self.history_input_list}')
        if self.llm_config.chatml:
            self.history_input_list[:] = [
                item for item in self.history_input_list
                if isinstance(item, dict) and ('content' in item)
            ]
        else:
            self.history_input_list[:] = [
                item for item in self.history_input_list
                if isinstance(item, dict) and ('type'in item and item['type'] =='message' or 'role' in item)
            ]
        # dyellow(f'history input after: {self.history_input_list}')

    def tools_from_response_to_chatml(self, request):
        # -----------------response.create()下的tool-----------------
        # {
        #   'type': 'function',
        #   'name': 'Folder_Tool',
        #   'description': '返回指定文件夹下所有文件和文件夹的名字信息。',
        #   'parameters': {
        #       'type': 'object',
        #       'properties': {
        #           'path': {
        #               'description': '文件夹所在的路径',
        #               'enum': None,
        #               'type': 'string'
        #           }
        #       },
        #       'required': ['path'],
        #       'additionalProperties': False
        #   },
        #   'strict': True
        # }

        # -----------------completions.create()下的tools-----------------
        # {
        #     "type": "function",
        #     "function": {
        #         "name": "Folder_Tool",
        #         "description": "返回指定文件夹下所有文件和文件夹的名字信息。",
        #         "parameters": {
        #             "type": "object",
        #             "properties": {
        #                 "path": {
        #                     "type": "string",
        #                     "description": "文件夹所在的路径"
        #                 }
        #             },
        #             "required": ["location"],
        #             "additionalProperties": False
        #         },
        #         "strict": True
        #     }
        # }

        if hasattr(request, 'tools') and request.tools:
            # for tool_dict in request.tools:
                # dyellow(tool_dict)

            for tool_dict in request.tools:
                # dgreen(f'tool_dict: {tool_dict}')

                # 1、将response tool除type外的部分装到新的chatml tool中
                response_tool = deepcopy(tool_dict)
                del response_tool.__dict__['type']
                tool_dict.function = deepcopy(response_tool)

                del tool_dict.__dict__['name']
                del tool_dict.__dict__['description']
                del tool_dict.__dict__['parameters']
                del tool_dict.__dict__['strict']

            # for tool_dict in request.tools:
                # dyellow(tool_dict)

        return request

    def _copy_request_and_modify_from_response_to_chatml(self, request:Response_Request):
        # 由于涉及Toolcall_Agent的对象实例的copy，deepcopy()会报错：cannot pickle '_thread.RLock' object
        request = deepcopy(request)

        # 因此，Pydantic v2情况下改为
        # print('-------------request:Tool_Request in _copy_request_and_modify_from_response_to_chatml--------------')
        # print(request)
        # print('------------/request:Tool_Request in _copy_request_and_modify_from_response_to_chatml-------------')

        # if hasattr(request, 'tools'):
        #     tools = request.tools
        #     del request.__dict__['tools']
        #     request = deepcopy(request)
        #     request.tools = tools  # 手动回填，避免深拷贝 func
        # else:
        #     request = deepcopy(request)

        # --------------------------response转chatml--------------------------
        # dred(request)
        # dred(request.tools)
        # request = request.model_dump()
        # request = request.model_dump(exclude_none=True)
        dcyan(f'response request: {request}')

        del request.__dict__['instructions']
        del request.__dict__['previous_response_id']
        del request.__dict__['tool_choice']
        del request.__dict__['parallel_tool_calls']

        request.max_tokens = request.max_output_tokens
        del request.__dict__['max_output_tokens']

        # request.pop('instructions')
        # request.pop('previous_response_id')
        # request.pop('tool_choice')
        # request.pop('parallel_tool_calls')

        # request['max_tokens'] = request['max_output_tokens']
        # request.pop('max_output_tokens')

        # dyellow('-------------response tool[0]--------------')
        # dpprint(request.tools[0])
        # dyellow('------------/response tool[0]--------------')

        request = self.tools_from_response_to_chatml(request=request)
        # dyellow('-----------chatml tool[0]------------')
        # dpprint(request.tools[0])
        # dyellow('----------/chatml tool[0]------------')

        request.extra_body = {'reasoning_effort': request.reasoning['effort']}
        del request.__dict__['reasoning']
        # request.pop('reasoning')

        # request['stream_options'] = {"include_usage": request['stream']}
        # request.pop('stream')

        dcyan(f'chatml request: {request}')

        return request

    def chatml_create(self, query, request:Response_Request, new_run)->Response_Result:
        # dred(f'--------------------old history input list-------------------------')
        # dred(self.history_input_list)
        # dred(f'-------------------/old history input list-------------------------')

        if self.history_input_list is None:
            self.history_input_list = [
                {"role": "system", "content": request.instructions},
                {"role": "user","content": query}
            ]
        else:
            if new_run:
                self.history_input_list += [
                    {"role": "user", "content": query}
                ]

        # dblue(f'--------------------new history input list-------------------------')
        # dred(self.history_input_list)
        # dblue(f'-------------------/new history input list-------------------------')

        # dyellow('===================================request.instructions====================================')
        # dpprint(request.model_dump())
        # dyellow(request.instructions)
        # dyellow('==================================/request.instructions====================================')

        dblue('=================================self.history_input_list===================================')
        for item in self.history_input_list:
            dblue(item)
        dblue('================================/self.history_input_list===================================')

        res = None
        call_id = ''
        response_result = Response_Result()

        try:
            dred(request)
            chatml_request = self._copy_request_and_modify_from_response_to_chatml(request)
            dred(chatml_request)

            # print('----------chatml_request------------')
            # print(chatml_request)
            # print('---------/chatml_request------------')
            temp_chatml_request = deepcopy(chatml_request)
            # print('----------temp_chatml_request------------')
            # print(temp_chatml_request)
            # print('---------/temp_chatml_request------------')

            if not temp_chatml_request.tools:
                del temp_chatml_request.tools    # 防止tools==[]交给api

            # -------------------------/response转chatml--------------------------

            # dblue('----------------------------self.history_input_list-------------------------------')
            # for item in self.history_input_list:
            #     dblue(item)
            # dblue('---------------------------/self.history_input_list-------------------------------')
            dred(temp_chatml_request.model_dump())
            dred(temp_chatml_request.model_dump(exclude_none=True))
            res = self.openai.chat.completions.create(messages=self.history_input_list, **temp_chatml_request.model_dump(exclude_none=True))
        except Exception as e:
            err(e)
            response_result.error = str(e)

        # dred('-----------------request.stream---------------------')
        # dred(request.stream)
        # dred('----------------/request.stream---------------------')
        if not request.stream:
            # 非stream输出
            dyellow('===================================chatml.choices[0].message====================================')
            dyellow('response: ', res)

            if res is None:
                self.history_input_list.append({'role': 'assistant', 'content': response_result.error})
            else:
                # 在history_input_list末尾添加上一次res的message
                if not self.llm_config.msgs_must_have_content:
                    dred(f'full_res({res})')
                    dred(f'chatml_output({res.choices[0].message.model_dump(exclude_none=True)})')
                    self.history_input_list.append(res.choices[0].message.model_dump(exclude_none=True))
                else:
                    # 有些模型要求message里必须有content，则msg如{'role': 'assistant', 'tool_calls': [...], 'reasoning_content': '...'}就不行
                    dict_have_content = res.choices[0].message.model_dump(exclude_none=True)
                    dict_have_content['content'] = dict_have_content.get('content', '')
                    self.history_input_list.append(dict_have_content)



            content = res.choices[0].message.content if hasattr(res.choices[0].message, 'content') else None
            if content:
                content = content.strip()
                dyellow('content: ', content.replace('\n', ' '))

            if hasattr(res.choices[0].message, 'reasoning_content'):
                reasoning_content = res.choices[0].message.reasoning_content
            else:
                reasoning_content = ''
            if reasoning_content:
                dyellow('reasoning_content: ', reasoning_content.replace('\n', ' '))

            if hasattr(res.choices[0].message, 'tool_calls') and res.choices[0].message.tool_calls:
                tool_arguments = res.choices[0].message.tool_calls[0].function.arguments
                tool_name = res.choices[0].message.tool_calls[0].function.name
                call_id = res.choices[0].message.tool_calls[0].id
            else:
                tool_arguments = ''
                tool_name = ''
            dyellow('tool_arguments: ', tool_arguments)
            dyellow('tool_name: ', tool_name)

            # dyellow(res.choices[0].message.content)
            dyellow('==================================/chatml.choices[0].message====================================')

            # -----------------------------添加到历史-------------------------------
            tool_call_error = ''
            if reasoning_content:
                # chatml下，reasoning添加到历史似乎导致上下文过长
                pass
                # self.history_input_list += [
                #     {"role": "assistant", "reasoning_content": reasoning_content}
                # ]
            elif content:
                pass
                # self.history_input_list += [
                #     {"role": "assistant", "content": content}
                # ]
            # else:
            #     dred(f'【Response_LLM_Client.chatml_create】Warning: chatml.create()返回失败.')
            # ----------------------------/添加到历史-------------------------------

            responses_result = Response_Result(
                reasoning = reasoning_content,
                output = content,
                function_tool_call = {'arguments': tool_arguments, 'call_id': call_id, 'name': tool_name},
                error=tool_call_error
            )

            # dyellow('==================================1111111====================================')
            # ----------------------注册tool func-------------------------
            # self.funcs = []  # 要先清除之前的tools
            # for tool in chatml_request.tools:
            #     func_dict = {
            #         'name' : tool.function.name,
            #         'func' : tool.function.func,
            #     }
            #     self.funcs.append(func_dict)
            # ---------------------/注册tool func-------------------------
            # dyellow('==================================2222222====================================')

            return responses_result
        else:
            # stream输出
            self._parse_chatml_stream(res)
            response_result.reasoning = self.reasoning_text
            response_result.output = self.output_text
            response_result.function_tool_call = self.function_tool_call
            dred(response_result)

            self.history_input_list.append(self.response_output) # 类似无stream时的self.history_input_list += res.output
            dred(f'self.history_input_list需要append: {self.response_output}')
            return response_result

    # 清除历史
    def clear_history(self):
        self.history_input_list = None

    def responses_create(self, query, request:Response_Request, new_run)->Response_Result:
        # dred(request.tools)
        # dred(request)
        # 第一次responses.create
        if self.history_input_list is None:
            self.history_input_list = [
                {
                    "role": "user",
                    "content": query,
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
                        "content": query,
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

        # dyellow('===================================request.instructions====================================')
        # dyellow(request.instructions)
        # dyellow('==================================/request.instructions====================================')

        dblue('=================================self.history_input_list===================================')
        for item in self.history_input_list:
            dblue(item)
        dblue('================================/self.history_input_list===================================')

        res = None
        response_result = Response_Result()

        try:
            # dpprint(request.model_dump(exclude_none=True))
            # print('----------request------------')
            # print(request)
            # print('---------/request------------')
            temp_response_request = deepcopy(request)
            if not temp_response_request.tools:
                del temp_response_request.tools  # 防止tools==[]交给api
                del temp_response_request.tool_choice
                del temp_response_request.parallel_tool_calls
                # temp_response_request.instructions='You are a helpful agent.'

            # print('----------temp_response_request------------')
            # print(temp_response_request)
            # print('---------/temp_response_request------------')

            dyellow('=================================request.tools===================================')
            if request.tools:
                for tool in request.tools:
                    dyellow(tool)
            dyellow('================================/request.tools===================================')
            # dred(temp_response_request.model_dump())
            # dred(temp_response_request.model_dump(exclude_none=True))
            res = self.openai.responses.create(input=self.history_input_list, **temp_response_request.model_dump(exclude_none=True))
        except Exception as e:
            err(e)
            response_result.error = str(e)

        if not request.stream:
            # 非stream输出
            # 不管responses_create是否为第一次，按照官方要求，添加responses.create()的response.output(后续需要在tool调用成功后，在history_input_list末尾添加{"type": "function_call_output", ...})
            if res:
                self.history_input_list += res.output
                dred(res.output)
                response_result = self._responses_result(res)
            else:
                dred(f'【Response_LLM_Client.responses_create】Warning: responses.create()返回失败.')
                self.history_input_list.append({'role': 'assistant', 'content': response_result.error})
                dprint('---------------------------------response_result(未调用工具)------------------------------------')
                dpprint(response_result.model_dump())
                dprint('--------------------------------/response_result(未调用工具)------------------------------------')

            # ----------------------注册tool func-------------------------
            # self.funcs = [] # 要先清除之前的tools
            # for tool in request.tools:
            #     func_dict = {
            #         'name' : tool.name,
            #         'func' : tool.func,
            #     }
            #     self.funcs.append(func_dict)
            # ---------------------/注册tool func-------------------------

            # 调用tool
            # response_result = self.call_tool(response_result)

            return response_result
        else:
            # stream输出
            self._parse_response_stream(res)
            response_result.reasoning = self.reasoning_text
            response_result.output = self.output_text
            response_result.function_tool_call = self.function_tool_call
            dred(response_result)

            self.history_input_list += self.response_output # 类似无stream时的self.history_input_list += res.output

            return response_result

    def on_reasoning(self, chunk):
        dred(chunk, end='', flush=True)

    def on_content(self, chunk):
        dgreen(chunk, end='', flush=True)

    def _parse_response_stream(self, response:Response):
        for item in response:
            # print(item)
            if item.type=='response.reasoning_text.delta':
                self.on_reasoning(chunk=item.delta)
                self.current_chunk = item.delta
            if item.type=='response.output_text.delta':
                self.on_content(chunk=item.delta)
                self.current_chunk = item.delta
            if isinstance(item, ResponseCompletedEvent):
                if hasattr(item, 'response'):
                    if hasattr(item.response, 'output'):
                        self.response_output = item.response.output
                        for output_item in item.response.output:
                            if output_item.type=='reasoning':
                                self.reasoning_text = output_item.content[0]['text']
                            if output_item.type=='message':
                                self.output_text = output_item.content[0].text
                            if output_item.type=='function_call':
                                self.tool_call_id = output_item.call_id
                                self.tool_arguments = output_item.arguments
                                self.tool_name = output_item.name
                                self.function_tool_call = {
                                    'arguments': self.tool_arguments,
                                    'call_id': self.tool_call_id,
                                    'name': self.tool_name,
                                }

    def _parse_chatml_stream(self, response:Response):
        dred(response)
        self.tool_arguments = ''
        self.reasoning_text = ''
        self.output_text = ''


        for item in response:
            if self.status.canceling:
                self.status.canceled = True
                return

            # print(item)
            if hasattr(item, 'choices'):
                delta = item.choices[0].delta
                # print(delta)
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    self.on_reasoning(chunk=delta.reasoning_content)
                    self.current_chunk = delta.reasoning_content
                    self.reasoning_text += self.current_chunk
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    if delta.tool_calls[0].function.name:
                        self.tool_name = delta.tool_calls[0].function.name
                    if delta.tool_calls[0].function.arguments:
                        self.tool_arguments += delta.tool_calls[0].function.arguments
                    if delta.tool_calls[0].id:
                        self.tool_call_id = delta.tool_calls[0].id
                if delta.content:
                    self.on_content(chunk=delta.content)
                    self.current_chunk = delta.content
                    self.output_text += self.current_chunk

        self.function_tool_call = {
            'arguments': self.tool_arguments,
            'call_id': self.tool_call_id,
            'name': self.tool_name,
        }
        # if self.tool_arguments:
        #     self.function_tool_call = {
        #         'arguments': self.tool_arguments,
        #         'call_id': self.tool_call_id,
        #         'name': self.tool_name,
        #     }
        # else:
        #     self.function_tool_call = {
        #         'arguments': '',
        #         'call_id': '',
        #         'name': '',
        #     }


        # dred('--------------------self.tool_arguments------------------------------')
        # dred(self.tool_arguments)
        # dred('-------------------/self.tool_arguments------------------------------')

        # 2025-10-13: g_local_gpt_oss_120b_mxfp4_lmstudio模型stream==True时，最终output时会输出 {'arguments': '', 'name': 'xxx'}这种有tool_name但没有arguments的情况，必须增加arguments判断，否则completions.create()报错
        if self.tool_name and self.tool_arguments:
        # if self.tool_name:
            # 如果有tool_call
            self.response_output = {
                'content': self.output_text,
                'role': 'assistant',
                'tool_calls': [
                    {
                        'id': self.tool_call_id,
                        'function': {
                            'arguments': self.tool_arguments,
                            'name': self.tool_name
                        },
                        'type': 'function',
                        'index': 0
                    }
                ],
                'reasoning_content': ''     # 这里暂时不向history添加reasoning内容
                # 'reasoning_content': self.reasoning_text
            }
        else:
            # 如果无tool_call
            self.response_output = {
                'content': self.output_text,
                'role': 'assistant',
                'reasoning_content': self.reasoning_text
            }

    def _responses_result(self, res:Response):
        # dprint(res)
        # dprint('------------------------------Response---------------------------------------')
        # dpprint(res.model_dump())
        # dprint('-----------------------------/Response---------------------------------------')

        response_result = Response_Result(previous_response_id = res.id)

        dprint()
        dprint(f'==========================================Response Items(res id: "{res.id}")==========================================')
        if res.output:
            dyellow(res.output)
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

        # dprint()
        # dprint('---------------------------------response_result(未调用工具)------------------------------------')
        # dpprint(response_result.model_dump())
        # dprint('--------------------------------/response_result(未调用工具)------------------------------------')

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
    from agent.tools.protocol import Tool_Parameters, Tool_Property
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
        # func=lambda a, b: {"result": a + b}
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
        # func=lambda a, b: {"result": a - b}
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
        # func=lambda a, b: {"result": a * b}
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
        # func=lambda a, b: {"result": a / b}
        # func=lambda a, b, unit: {"result": a / b, "unit": unit}
    )

    # from agent.tools.folder_tool import Folder_Tool
    # fold_tool = Folder_Tool.get_tool_param_dict()

    # tools = []
    # tools = [div_tool]
    tools = [add_tool, sub_tool, mul_tool, div_tool]

    # -------------打印输入参数--------------
    # dpprint(response_request.model_dump())

    client = Response_and_Chatml_LLM_Client(llm_config=llm_protocol.g_online_groq_gpt_oss_120b)
    # client = Response_and_Chatml_LLM_Client(llm_config=llm_protocol.g_online_groq_gpt_oss_20b)
    client.init()

    query = '请告诉我2356/3567等于多少，保留10位小数，要调用工具计算，不能直接心算'
    # query = '请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'
    response_request = Response_Request(
        model=client.llm_config.llm_model_id,
        tools=tools,
        temperature=client.llm_config.temperature,
        top_p=client.llm_config.top_p,
        max_output_tokens=client.llm_config.max_new_tokens,
        reasoning={"effort": client.llm_config.reasoning_effort},
        # stream=True,
    )
    responses_result = client.responses_create(query=query, request=response_request, new_run=False)

    dprint()
    dprint('-------------------------responses_result--------------------------------')
    pprint(responses_result.model_dump())
    dprint()
    dprint(f'responses_result.output: {responses_result.output!r}')
    dprint('-------------------------responses_result--------------------------------')
    # dprint(f'responses_result.function_tool_call: {responses_result.function_tool_call}')

    while not hasattr(responses_result, 'output') or responses_result.output=='' :
        responses_result = client.responses_create(query=query, request=response_request, new_run=False)
        dprint(f'responses_result: {responses_result!r}')

        if not responses_result.output:
            continue

        if responses_result.output != '':
            dprint('-----------------------------------最终结果---------------------------------------------')
            dprint(responses_result.output)
            dprint('-----------------------------------最终结果---------------------------------------------')
            dgreen('-----------------------------------最终结果---------------------------------------------')
            dgreen(responses_result.output)
            dgreen('-----------------------------------最终结果---------------------------------------------')
            break

def main_chatml_llm_client():
    from agent.tools.protocol import Tool_Parameters, Tool_Property
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
        # func=lambda a, b: {"result": a + b}
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
        # func=lambda a, b: {"result": a - b}
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
        # func=lambda a, b: {"result": a * b}
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
        # func=lambda a, b: {"result": a / b}
        # func=lambda a, b, unit: {"result": a / b, "unit": unit}
    )

    # from agent.tools.folder_tool import Folder_Tool
    # fold_tool = Folder_Tool.get_tool_param_dict()

    # tools = []
    # tools = [div_tool]
    tools = [add_tool, sub_tool, mul_tool, div_tool]

    # -------------打印输入参数--------------
    # dpprint(response_request.model_dump())

    # client = Response_and_Chatml_LLM_Client(llm_config=llm_protocol.g_online_qwen3_next_80b_instruct)
    client = Response_and_Chatml_LLM_Client(llm_config=llm_protocol.g_online_qwen3_next_80b_thinking)
    # client = Response_and_Chatml_LLM_Client(llm_config=llm_protocol.g_online_groq_gpt_oss_20b)
    client.init()

    # query = '写一首几行字的诗'
    query = '请告诉我2356/3567等于多少，保留10位小数，要调用工具计算，不能直接心算'
    # query = '请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'
    response_request = Response_Request(
        model=client.llm_config.llm_model_id,
        tools=tools,
        temperature=client.llm_config.temperature,
        top_p=client.llm_config.top_p,
        max_output_tokens=client.llm_config.max_new_tokens,
        reasoning={"effort": client.llm_config.reasoning_effort},
        stream=True,
    )
    responses_result = client.chatml_create(query=query, request=response_request, new_run=False)

    dprint()
    dprint('-------------------------responses_result--------------------------------')
    pprint(responses_result.model_dump())
    dprint()
    dprint(f'responses_result.output: {responses_result.output!r}')
    dprint('-------------------------responses_result--------------------------------')
    # dprint(f'responses_result.function_tool_call: {responses_result.function_tool_call}')

    # while not hasattr(responses_result, 'output') or responses_result.output=='' :
    #     responses_result = client.responses_create(query=query, request=response_request, new_run=False)
    #     dprint(f'responses_result: {responses_result!r}')
    #
    #     if not responses_result.output:
    #         continue
    #
    #     if responses_result.output != '':
    #         dprint('-----------------------------------最终结果---------------------------------------------')
    #         dprint(responses_result.output)
    #         dprint('-----------------------------------最终结果---------------------------------------------')
    #         dgreen('-----------------------------------最终结果---------------------------------------------')
    #         dgreen(responses_result.output)
    #         dgreen('-----------------------------------最终结果---------------------------------------------')
    #         break

def main_response_agent():
    from agent.tools.protocol import Tool_Parameters, Tool_Property
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

    client = Response_and_Chatml_LLM_Client(llm_config=llm_protocol.g_online_groq_gpt_oss_20b)
    client.init()
    client.legacy_agent_run(query=query, tools=tools)

def main_response_llm_client_chat():
    client = Response_and_Chatml_LLM_Client(llm_config=llm_protocol.g_online_groq_gpt_oss_20b)
    client.init()

    query = '写一首20字的诗'
    response_request = Response_Request(
        model=client.llm_config.llm_model_id,
        temperature=client.llm_config.temperature,
        top_p=client.llm_config.top_p,
        max_output_tokens=client.llm_config.max_new_tokens,
        reasoning={"effort": client.llm_config.reasoning_effort},
        stream=True,
    )
    responses_result = client.responses_create(query=query, request=response_request, new_run=False)

    dprint()
    dprint('-------------------------responses_result--------------------------------')
    pprint(responses_result.model_dump())
    dprint()
    dprint(f'responses_result.output: {responses_result.output!r}')
    dprint('-------------------------responses_result--------------------------------')

    while not hasattr(responses_result, 'output') or responses_result.output=='' :
        responses_result = client.responses_create(query=query, request=response_request, new_run=False)
        dprint(f'responses_result: {responses_result!r}')

        if not responses_result.output:
            continue

        if responses_result.output != '':
            dprint('-----------------------------------最终结果---------------------------------------------')
            dprint(responses_result.output)
            dprint('-----------------------------------最终结果---------------------------------------------')
            dgreen('-----------------------------------最终结果---------------------------------------------')
            dgreen(responses_result.output)
            dgreen('-----------------------------------最终结果---------------------------------------------')
            break

def main_chatml_llm_client_chat():
    dred(llm_protocol.g_online_groq_kimi_k2)
    client = Response_and_Chatml_LLM_Client(llm_config=llm_protocol.g_online_deepseek_reasoner)
    client.init()

    query = '写一首几行字的诗'
    response_request = Response_Request(
        model=client.llm_config.llm_model_id,
        temperature=client.llm_config.temperature,
        top_p=client.llm_config.top_p,
        max_output_tokens=client.llm_config.max_new_tokens,
        reasoning={"effort": client.llm_config.reasoning_effort},
        stream=True,
    )
    responses_result = client.chatml_create(query=query, request=response_request, new_run=False)

    dprint()
    dprint('-------------------------responses_result--------------------------------')
    pprint(responses_result.model_dump())
    dprint()
    dprint(f'responses_result.output: {responses_result.output!r}')
    dprint('-------------------------responses_result--------------------------------')


if __name__ == "__main__":
    # main_response_request_pprint()
    # main_response_llm_client()
    # main_response_llm_client_chat()
    main_chatml_llm_client()
    # main_chatml_llm_client_chat()
    # main_response_llm_client()
    # main_response_agent()