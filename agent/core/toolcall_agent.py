# --------------------------------openai的harmony response接口的主要特性--------------------------------
# 1、response.create()中，input对应completions.create中的messages，且必须为下述格式：
#       {'role': 'user', 'content': '你好，我的名字是土土'}
#       {'role': 'assistant', 'content': '你好，土土！请告诉我需要我帮你完成什么任务。祝你愉快！'}
#   注意下述"type": "message"起始的格式是错误的，llm无法把其当作有效上下文，但又不报错
#       {
#         "type": "message",
#         "role": "user",
#         "content": [{"type": "input_text", "text": '你好，我的名字是土土'}],
#       }
# 2、response.create()中，instructions对应completions.create中的system prompt
# 3、response.create()中，调用工具后，直接input += res.output，且input.append下述特定格式的tool result后，并将其作为新的input再次调用response.create()即可进行连续工具调用
#         {
#             "type": "function_call_output",
#             "call_id": "call_456",
#             "output": "Weather(city='Tokyo', temperature_range='14-20C', conditions='Sunny')"
#         }
# 4、response.create()中，在res输出output(assistant的text输出）后，需要一个新的{'role': 'user', 'content': ...}开启下一轮对话或工具调用任务
# 5、response.create()连续调用工具完成任务后会输出output，此时若继续调用response.create()进行新一轮run，似乎必须将input历史中的ResponseReasoningItem、ResponseFunctionToolCall、ResponseOutputMessage等清除，不然会报错
# 6、chatml的tool_call过程，与response的tool_call不太一样，关键点两个：
#   1) 输入tools信息并返回res后，要msgs.append(resp.choices[0].message.model_dump(exclude_none=True)), 类似response中的input += res.output
#   2) 获得工具调用结果后，要msgs.append({ "role": "tool", "tool_call_id": call_id, "content": f'tool call result: "{output}", tool call error: "{error}".' }), 这里必须要有call_id, 且call_id必须和前一条message中的'tool_calls'信息中的'id'一致

from pydantic import BaseModel
from typing import List, Dict, Any, Type, Literal, Optional, Callable

import config
import llm_protocol
from llm_protocol import LLM_Config
from agent.tools.protocol import Tool_Request
from tools.llm.response_and_chatml_api_client import Response_and_Chatml_LLM_Client, Response_Result, Response_Request

from agent.core.agent_config import Agent_Config
from agent.core.protocol import Query_Agent_Context, Agent_Status, Agent_Tool_Result
from agent.tools.legacy_protocol import Tool_Call_Paras, Action_Result

from config import dred, dgreen, dblue, dyellow, dcyan
from pprint import pprint
from uuid import uuid4
import json

from console import err, agent_query_output, agent_tool_chosen_output, agent_tool_result_output, agent_finished_output
from agent.core.mcp.mcp_manager import get_mcp_server_tool_names, get_mcp_server_tools

DEBUG = config.Global.app_debug

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def dpprint(*args, **kwargs):
    if DEBUG:
        pprint(*args, **kwargs)

class Toolcall_Agent:
    def __init__(self, agent_config:Agent_Config):

        self.llm_config = agent_config.llm_config
        self.response_llm_client = Response_and_Chatml_LLM_Client(self.llm_config)
        self.agent_config = agent_config

        # tool的funcs的管理: tool_name <--> tool_func（含agent_as_tool的func(即agent_as_tool.run))
        self.tool_funcs_dict:Dict[str, Callable] = {}

        # 自己的id
        self.agent_id = str(uuid4())
        self.agent_level = 0            # 用于表示agent是顶层agent，还是下级的agent_as_tool
        self.sub_agents = []  # lower的agent_as_tool的列表
        # 多层agent体系中的顶层agent的id
        self.top_agent_id = self.agent_config.top_agent_id if self.agent_config.top_agent_id else self.agent_id

        # 经验
        self.current_exp_str = ''

        # agent最大出错次数
        self.agent_max_error_retry = self.agent_config.agent_max_error_retry
        # agent最大次数
        self.agent_max_retry = self.agent_config.agent_max_retry

        self.agent_status = Agent_Status()

        # self.final_answer_flag = '【任务完成】'
        # self.decide_final_answer_prompt = f'当完成任务时，请输出"{self.final_answer_flag}"，否则系统无法判断何时结束任务。'

    # 用于尝试cancel当前的任务
    def set_cancel(self):
        self.agent_status.canceled = False
        self.agent_status.canceling = True

        # 尝试cancel所有lower_agent_as_tool
        for sub_agent in self.sub_agents:
            sub_agent.set_cancel()

    # 用于建立agent和sub_agent之间的关联（如cancel的遍历、level计算的遍历、设置top_agent_id的遍历）
    def register_sub_agents(self, sub_agent_data_list):
        # 注册lower的agents
        for agent_data in sub_agent_data_list:
            self.sub_agents.append(agent_data.agent)

        print('------------------------------所有需要遍历上下层agents的操作------------------------------')
        # 1、尝试计算本agent及下层所有agent的agent_level
        self._calculate_all_agents_level()
        # 2、遍历设置top_agent_id
        self._calculate_all_agents_top_agent_id()
        print('-----------------------------/所有需要遍历上下层agents的操作------------------------------')

    # 是否为agent as tool(sub-agent)
    def is_sub_agent(self):
        if self.agent_config.as_tool_name:
            return True
        else:
            return False

    # 在所有层agent都注册完之后，计算所有层agent的top_agent_id
    def _calculate_all_agents_top_agent_id(self, top_agent_id=None):
        if top_agent_id is None:
            top_agent_id = self.top_agent_id
            print(f'----------agent_id={self.agent_id}, top_agent_id={self.top_agent_id}, agent_name={self.agent_config.agent_name}------------')

        for sub_agent in self.sub_agents:
            sub_agent.top_agent_id = top_agent_id
            print(f'----------agent_id={sub_agent.agent_id}, set top_agent_id={sub_agent.top_agent_id}, agent_name={sub_agent.agent_config.agent_name}------------')
            sub_agent._calculate_all_agents_top_agent_id(top_agent_id=top_agent_id)

    # 在所有层agent都注册完之后，计算所有层agent的agent_level
    def _calculate_all_agents_level(self, agent_level=0):
        # 仅当本agent为顶层agent时，计算本agent及下面所有层agent的agent_level，
        if not self.is_sub_agent():
            self.agent_level = agent_level
            print(f'----------agent_id={self.agent_id}, set agent_level={agent_level}, agent_name={self.agent_config.agent_name}------------')
            for sub_agent in self.sub_agents:
                sub_agent._calculate_all_agents_level(self.agent_level + 1)
        else:
            # dyellow(f'【Toolcall_Agent.calculate_all_agents_level】warning: 未从顶层agent开始计算所有层agent的level.')
            self.agent_level = agent_level
            print(f'----------agent_id={self.agent_id}, set agent_level={agent_level}, agent_name={self.agent_config.agent_name}------------')
            for sub_agent in self.sub_agents:
                sub_agent._calculate_all_agents_level(self.agent_level + 1)

    # 初始化self.tool_funcs_dict
    def _set_funcs(self, tool_requests, tool_funcs):
        for tool_request, tool_func in zip(tool_requests, tool_funcs):
            self.tool_funcs_dict[tool_request.name] = tool_func

    # 计算agent的level数(完整版: 应该由agent_manager递归访问上级agent，直到agent_id==top_agent_id判断，并通过agent_manager调用agent.set_agent_level()设置)
    # def _calculate_agent_level(self):
    #     if self.agent_config.as_tool_name:
    #         self.agent_level = 1
    #     else:
    #         self.agent_level = 0
    def set_agent_level(self, agent_level):
        self.agent_level = agent_level

    def init(self,
             tool_requests,     # 所有的tool的描述
             tool_funcs         # 所有的tool的回调func
             ):
        self.response_llm_client.init()
        self._set_funcs(tool_requests, tool_funcs)
        # self._calculate_agent_level()

        # 若为lower agent，则设置self.history为False
        if self.agent_config.as_tool_name:
            self.agent_config.has_history = False

    def _call_tool(self,
                   response_result:Response_Result, # response_api的调用结果
                   tool_call_paras:Tool_Call_Paras, # agent调度的上下文
                   ):
        tool_call = response_result.function_tool_call
        if tool_call and 'name' in tool_call:
            tool_name = tool_call['name']

            func = self.tool_funcs_dict.get(tool_name)
            if func:
            # for func in self.response_llm_client.funcs:
            #     if func['name'] in tool_name:   # vllm的response api有时候会出错，如：'name': 'div_tool<|channel|>json' 而不是 'name': 'div_tool'
                # if tool_name == func['name']:
                try:
                    agent_tool_chosen_output(tool_name=tool_name, tool_paras=tool_call['arguments'], agent_level=self.agent_level)
                    args = json.loads(tool_call['arguments'])

                    # -----------------------------工具调用-----------------------------
                    # tool_call_paras.callback_tool_paras_dict = args
                    # tool_call_paras.callback_tool_call_id = str(uuid4())    # 生成tool_call_id, 主要用于resource_id
                    func_rtn = func(tool_call_paras=tool_call_paras, **args)
                    # func_rtn = func['func'](tool_call_paras=tool_call_paras, **args)
                    # ----------------------------/工具调用-----------------------------

                    dprint('-----------------------------工具调用结果-------------------------------')
                    dprint(f'tool_name = "{tool_name}"')
                    dprint(func_rtn)
                    dprint('----------------------------/工具调用结果-------------------------------')
                    if isinstance(func_rtn, Agent_Tool_Result):
                        response_result.tool_call_result = json.dumps(func_rtn.model_dump(), ensure_ascii=False)
                    elif isinstance(func_rtn, Response_Result):
                        # 如果是agent as tool
                        agent_tool_result = Agent_Tool_Result(result_summary=func_rtn.agent_as_tool_call_result)     # 由于是agent as tool，在agent.run()中，func_rtn.agent_as_tool_call_result已设置为agent.agent_status.final_answer
                        response_result.tool_call_result = json.dumps(agent_tool_result.model_dump(), ensure_ascii=False)
                    else:
                        dyellow(f'【Toolcall_Agent._call_tool()】warning: 工具调用结果既不是Agent_Tool_Result也不是Response_Result.')
                        response_result.tool_call_result = json.dumps(func_rtn, ensure_ascii=False)

                    # tool_call_result_item = {
                    #     "type": "function_call_output",
                    #     "call_id": tool_call['call_id'],
                    #     "output": json.dumps({tool_call['name']: response_result.tool_call_result}),
                    #     "error": response_result.error
                    # }

                    self.response_llm_client.history_input_add_tool_call_result_item(
                        arguments=tool_call['arguments'],
                        call_id=tool_call['call_id'],
                        output=json.dumps({tool_call['name']: response_result.tool_call_result}, ensure_ascii=False),
                        error=response_result.error
                    )
                    agent_tool_result_output(json.loads(response_result.tool_call_result), agent_level=self.agent_level)
                    # agent_tool_result_output(json.loads(response_result.tool_call_result).get('result'))
                    # self.response_llm_client.history_input_list.append(tool_call_result_item)

                    return response_result
                except Exception as e:
                    err(e)
                    response_result.error = e
                    # response_result.tool_call_result = e
                    dred(f'【Toolcall_Agent._call_tool()】responses_result.error: {e!r}')
                    agent_tool_result_output(response_result.error, agent_level=self.agent_level)
                    return response_result

        return response_result

    # run之前的初始化
    def _before_run(self, query):
        self.agent_status.querying = True
        self.agent_status.canceled = False
        self.agent_status.canceling = False
        self.agent_status.final_answer = ''
        agent_query_output(query, agent_level=self.agent_level)

    # run之后的处理
    def _after_run(self):
        self.agent_status.query_task_finished = True
        self.agent_status.querying = False

        # --------------------------------
        # 一轮run结束后，需要将input_list中的ResponseReasoningItem、ResponseFunctionToolCall和ResponseOutputMessage清除
        # 否则server会报validation errors for ValidatorIterator的错误
        self.response_llm_client.history_input_reduce_content_after_this_run()

        dgreen('-----------------------------------最终结果---------------------------------------------')
        dgreen(self.agent_status.final_answer)
        dgreen('-----------------------------------最终结果---------------------------------------------')
        # print(f'final: {self.agent_status.final_answer}')
        agent_finished_output(self.agent_status.final_answer, agent_level=self.agent_level)

    # 清除历史
    def clear_history(self):
        self.response_llm_client.clear_history()
        dred('--------------------Toolcall_Agent.clear_history()已调用--------------------')

    def run(self, instruction, tool_call_paras:Tool_Call_Paras=None):
        self._before_run(instruction)

        if not self.agent_config.has_history:
            # 如果不含hisotry，则清除history
            self.clear_history()

        use_chatml = self.response_llm_client.llm_config.chatml

        # query_with_final_answer_flag = query + '\n' + self.decide_final_answer_prompt
        # dblue(f'-------------------------------query_with_final_answer_flag-------------------------------')
        # dblue(query_with_final_answer_flag)
        # dblue(f'------------------------------/query_with_final_answer_flag-------------------------------')

        agent_err_count = 0
        agent_count = 0

        response_request = Response_Request(
            # instructions=query_with_final_answer_flag,  # 这里仍然是'请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'
            # input=query_with_final_answer_flag,       # 第一次请求input用query，第二次及以后的请求，input实际用了self.history_input_list
            # instructions='继续调用工具直到完成user的任务',
            model=self.llm_config.llm_model_id,
            tools=self.agent_config.all_tool_requests,
            temperature=self.llm_config.temperature,
            top_p=self.llm_config.top_p,
            max_output_tokens=self.llm_config.max_new_tokens,
            reasoning={"effort": self.llm_config.reasoning_effort},
        )
        responses_result = Response_Result()

        # 只有当res包含output、且不包含function_tool_call时，才退出
        while (responses_result.function_tool_call and responses_result.function_tool_call['name']) or (not hasattr(responses_result, 'output') or responses_result.output=='' or responses_result.output is None):
        # while (responses_result.function_tool_call) or (not hasattr(responses_result, 'output') or responses_result.output=='' or responses_result.output is None):

            # 处理cancel
            if self.agent_status.canceling:
                self.agent_status.canceled = True
                break

            agent_count += 1
            if agent_err_count >= self.agent_max_error_retry:
                dred(f'【Response_API_Tool_Agent.run()】出错次数超出agent_max_error_retry({self.agent_max_error_retry})，退出循环.')
                break

            if agent_count >= self.agent_max_retry:
                dred(f'【Response_API_Tool_Agent.run()】调用次数超出agent_max_retry({self.agent_max_retry})，退出循环.')
                break

            try:
                # query = query_with_final_answer_flag

                new_run = False
                if self.agent_status.query_task_finished:
                    new_run = True
                    self.agent_status.query_task_finished = False

                # dred(tools)
                if use_chatml:
                    responses_result = self.response_llm_client.chatml_create(query=instruction, request=response_request, new_run=new_run)
                else:
                    responses_result = self.response_llm_client.responses_create(query=instruction, request=response_request, new_run=new_run)
                # dpprint(responses_result.model_dump())
                dblue(f'-------------------------responses_result(use_chatml: {use_chatml})-----------------------------')
                for item in responses_result:
                    dblue(item)
                dblue(f'------------------------/responses_result-----------------------------')
            except Exception as e:
                err(e)
                agent_err_count += 1
                responses_result.error = str(e)
                continue

            # tool_call_paras = None

            # tool解析出错等情况下
            if responses_result.error:
                continue

            # 有时候没有调用工具，直接output
            if not responses_result.function_tool_call:
                if responses_result.output:
                    self.agent_status.final_answer = responses_result.output.strip()
                else:
                    self.agent_status.final_answer = responses_result.output

                self.response_llm_client.history_input_add_output_item(self.agent_status.final_answer)
                self._after_run()
                return self.agent_status
            # if not responses_result.function_tool_call:
            #     # dred(f'function_tool_call为空2, responses_result.output:{responses_result.output!r}')
            #     if self.final_answer_flag in responses_result.output:
            #         self.agent_status.final_answer = responses_result.output.replace(self.final_answer_flag, '').strip()
            #
            #         self.response_llm_client.history_input_add_output_item(self.agent_status.final_answer)
            #         self._run_after()
            #         return self.agent_status
            #     else:
            #         continue
            if use_chatml:
                tool_params_dict = json.loads(responses_result.function_tool_call['arguments']) if responses_result.function_tool_call['arguments'] else None
            else:
                tool_params_dict = json.loads(responses_result.function_tool_call['arguments'])
            tool_call_paras = Tool_Call_Paras(
                callback_top_agent_id=self.top_agent_id,
                callback_tool_paras_dict=tool_params_dict,
                callback_agent_config=self.agent_config,
                callback_agent_id=self.agent_id,
                # callback_tool_call_id=str(uuid4()),
                # callback_last_tool_ctx=last_tool_ctx,
                # callback_client_ctx=context,
                callback_father_agent_exp=self.current_exp_str
            )

            dyellow('-----------------------------tool_call_paras----------------------------------')
            for item in tool_call_paras:
                dyellow(item)
            dyellow('----------------------------/tool_call_paras----------------------------------')
            responses_result = self._call_tool(responses_result, tool_call_paras)
            # responses_result = self.response_llm_client.legacy_call_tool(responses_result)

            if responses_result is None:
                continue

        if self.agent_status.canceled:
            # canceled退出
            canceled_output = f'agent任务已被取消(agent name: {self.agent_config.agent_name!r}).'
            agent_finished_output(canceled_output, agent_level=self.agent_level)
            self.agent_status.querying = False
        else:
            # 正常退出
            self.agent_status.final_answer = responses_result.output.strip()

            self.response_llm_client.history_input_add_output_item(self.agent_status.final_answer)
            self._after_run()

        if self.agent_config.as_tool_name:
            # 如果是agent as tool，则返回是tool_call结果
            responses_result.agent_as_tool_call_result = self.agent_status.final_answer

        return responses_result

def main_response_agent():
    # add_tool = Tool_Request(
    #     name='add_tool',
    #     description='加法计算工具',
    #     parameters=Tool_Parameters(
    #         properties={
    #             'a': Tool_Property(type='number', description='参数1'),
    #             'b': Tool_Property(type='number', description='参数2'),
    #             # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
    #         },
    #         required=['a', 'b'],
    #     ),
    #     func=lambda a, b, **kwargs: {"result": a + b}
    #     # func=lambda a, b, unit: {"result": a + b, "unit": unit}
    # )
    # sub_tool = Tool_Request(
    #     name='sub_tool',
    #     description='减法计算工具',
    #     parameters=Tool_Parameters(
    #         properties={
    #             'a': Tool_Property(type='number', description='参数1'),
    #             'b': Tool_Property(type='number', description='参数2'),
    #             # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
    #         },
    #         required=['a', 'b'],
    #     ),
    #     func=lambda a, b, **kwargs: {"result": a - b}
    #     # func=lambda a, b, unit: {"result": a - b, "unit": unit}
    # )
    # mul_tool = Tool_Request(
    #     name='mul_tool',
    #     description='乘法计算工具',
    #     parameters=Tool_Parameters(
    #         properties={
    #             'a': Tool_Property(type='number', description='参数1'),
    #             'b': Tool_Property(type='number', description='参数2'),
    #             # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
    #         },
    #         required=['a', 'b'],
    #     ),
    #     func=lambda a, b, **kwargs: {"result": a * b}
    #     # func=lambda a, b, unit: {"result": a * b, "unit": unit}
    # )
    # div_tool = Tool_Request(
    #     name='div_tool',
    #     description='除法计算工具',
    #     parameters=Tool_Parameters(
    #         properties={
    #             'a': Tool_Property(type='number', description='参数1'),
    #             'b': Tool_Property(type='number', description='参数2'),
    #             # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
    #         },
    #         required=['a', 'b'],
    #     ),
    #     func=lambda a, b, **kwargs: {"result": a / b}
    #     # func=lambda a, b, unit: {"result": a / b, "unit": unit}
    # )

    from agent.tools.folder_tool import Folder_Tool
    from agent.tools.office_tool import Write_Chapter_Tool
    from agent.tools.protocol import get_tool_requests_and_tool_funcs_from_tool_classes

    tool_requests, funcs = get_tool_requests_and_tool_funcs_from_tool_classes([Folder_Tool, Write_Chapter_Tool])
    # tool_request_and_func_pair1 = get_tool_request_and_func_from_tool_class(Folder_Tool)
    # tool_request_and_func_pair2 = get_tool_request_and_func_from_tool_class(Write_Chapter_Tool)
    #
    # tool_request_and_func_pairs = [tool_request_and_func_pair1, tool_request_and_func_pair2]
    # tool_requests, funcs = zip(*tool_request_and_func_pairs)

    agent_config = Agent_Config(
        agent_name = 'agent for search folder',
        allowed_local_tool_names=['Folder_Tool'],
        all_tool_requests=tool_requests,
        # llm_config=llm_protocol.g_local_qwen3_30b_thinking,
        # llm_config=llm_protocol.g_local_qwen3_30b_chat,
        # llm_config=llm_protocol.g_online_deepseek_chat,
        # llm_config=llm_protocol.g_online_groq_gpt_oss_20b,
        # llm_config=llm_protocol.g_online_groq_gpt_oss_120b,
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4,
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4_lmstudio,
        llm_config=llm_protocol.g_local_gpt_oss_120b_mxfp4_lmstudio,
        # has_history=False,
        has_history=True,
    )

    query = '请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，递归搜索所有子文件夹直到准确找到该文件'
    # query = '请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'
    # query = '你是谁？'

    agent = Toolcall_Agent(agent_config=agent_config)
    agent.init(tool_requests, funcs)
    print(f'agent.tool_funcs_dict: {agent.tool_funcs_dict}')
    # agent.run(instruction=query, tools=tools)

    # agent.run(instruction='你好，我的名字是土土', tools=tools)
    agent.run(instruction=query)
    # agent.run(instruction=query, tools=tools)
    agent.run(instruction='你还记得我的名字是什么吗？还有之前你已经找到了file_to_find.txt，告诉我具体是在哪里找到')

    # agent.run(instruction='你好，我的名字是土土', tools=tools)
    # agent.run(instruction='你还记得我的名字是什么吗？', tools=tools)

def main_response_agent_mcp_nginx():
    from openai import OpenAI
    import httpx
    import llm_protocol
    import config

    server_url1 = "https://powerai.cc:8011/mcp/sqlite/sse"
    server_url2 = "http://localhost:8789/sse"
    # server_url = "https://powerai.cc:8011/mcp/everything/sse"
    tool_requests1, tool_funcs1 = get_mcp_server_tools(server_url1)
    tool_requests2, tool_funcs2 = get_mcp_server_tools(server_url2)
    tool_names = get_mcp_server_tool_names(server_url1) + get_mcp_server_tool_names(server_url2)
    print(tool_names)
    # print(tools)
    # for tool in tools:
    #     print(tool)

    agent_config = Agent_Config(
        agent_name='MCP agent',
        allowed_local_tool_names=tool_names,
        all_tool_requests=tool_requests1+tool_requests2,
        # llm_config=llm_protocol.g_online_groq_gpt_oss_20b,
        # llm_config=llm_protocol.g_online_groq_gpt_oss_120b,
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4,
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4_lmstudio,
        # llm_config=llm_protocol.g_online_qwen3_next_80b_instruct,
        # llm_config=llm_protocol.g_online_qwen3_next_80b_thinking,
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4,
        llm_config=llm_protocol.g_local_gpt_oss_120b_mxfp4_lmstudio,
        # llm_config=llm_protocol.g_online_deepseek_chat,
        # llm_config=llm_protocol.g_local_qwen3_30b_gptq_int4,
        has_history=True,
    )
    agent = Toolcall_Agent(agent_config=agent_config)
    agent.init(tool_requests1+tool_requests2, tool_funcs1+tool_funcs2)
    # agent.run(query='列出所有表格名称', tools=tools)
    # agent.run(query='查看通信录表的数据', tools=tools)

    while True:
        agent.run(instruction=input('请输入你的指令：'))

def main_response_agent_mcp_server():
    from openai import OpenAI
    import httpx
    import llm_protocol

    http_client = httpx.Client(proxy=config.g_vpn_proxy)
    llm_config = llm_protocol.g_online_groq_gpt_oss_20b
    client = OpenAI(
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        http_client=http_client,
    )

    resp = client.responses.create(
        model=llm_config.llm_model_id,
        tools=[
            {
                "type": "mcp",
                "server_label": "dmcp",
                "server_description": "A Dungeons and Dragons MCP server to assist with dice rolling.",
                "server_url": "https://dmcp-server.deno.dev/sse",
                "require_approval": "never",
            },
        ],
        input="Roll 2d4+1",
    )

    print('----------------------resp.output--------------------------')
    for item in resp.output:
        print(item)
    print('---------------------/resp.output--------------------------')
    print(resp.output_text.replace('\n', ''))

def main_office_agent():
    # ---------------------------测试阶段用agent控制libre-office---------------------------
    # 1、前端：EditorPanel.tsx，第27行的5112临时改为5113，然后运行remote_dev.sh
    # 2、后端：office_tool.py，第1008行改用5113端口，第1132行的DEBUG改为True(不做connection和agent_id对应)，然后启动agent_fastapi_server.py
    # 3、运行本程序
    # --------------------------/测试阶段用agent控制libre-office---------------------------

    print(f'office_agent started.')

    from agent.tools.office_tool import Write_Chapter_Tool
    write_chapter_tool = Write_Chapter_Tool.get_tool_param_dict()
    Write_Chapter_Tool.init_ws_server()

    tools = [write_chapter_tool]
    dprint('--------------------tools[0]----------------------')
    dpprint(write_chapter_tool)
    dprint('-------------------/tools[0]----------------------')

    agent_config = Agent_Config(
        agent_name = 'agent for office docx file editing',
        allowed_local_tool_names=['Write_Chapter_Tool'],
        # llm_config=llm_protocol.g_local_qwen3_30b_thinking,
        # llm_config=llm_protocol.g_local_qwen3_30b_chat,
        # llm_config=llm_protocol.g_online_deepseek_chat,
        # llm_config=llm_protocol.g_online_groq_gpt_oss_20b,
        # llm_config=llm_protocol.g_online_groq_gpt_oss_120b,
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4,
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4_lmstudio,
        llm_config=llm_protocol.g_online_qwen3_next_80b_instruct,
        # llm_config=llm_protocol.g_local_gpt_oss_120b_mxfp4_lmstudio,
        has_history=True,
    )

    agent = Toolcall_Agent(agent_config=agent_config)
    agent.init()

    while True:
        # query = '请帮我编制报告，项目名称是"基于AI-native框架的自主化咨询设计系统"，投资控制在100万元左右，章节编制需求是3.2章、编写项目必要性，项目关键诉求是方案具有前瞻性。'
        agent.run(instruction=input('请输入你的指令：'), tools=tools)

if __name__ == "__main__":
    main_response_agent()
    # main_response_agent_mcp_nginx()     # mcp经过nginx映射后测试可用，但目前groq api不支持调用mcp
    # main_response_agent_mcp_server()
    # main_office_agent()