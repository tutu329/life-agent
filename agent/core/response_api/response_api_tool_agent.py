import config
import llm_protocol
from llm_protocol import LLM_Config
from agent.tools.protocol import Tool_Call_Paras
from tools.llm.response_api_client import Response_LLM_Client, Response_Result, Tool_Request, Tool_Parameters, Tool_Property, Response_Request

from agent.core.agent_config import Agent_Config
from agent.core.protocol import Query_Agent_Context, Agent_Status
from agent.tools.protocol import Tool_Call_Paras, Action_Result

from config import dred, dgreen, dblue, dyellow, dcyan
from pprint import pprint
from uuid import uuid4
import json

DEBUG = True
# DEBUG = False

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def dpprint(*args, **kwargs):
    if DEBUG:
        pprint(*args, **kwargs)

class Response_API_Tool_Agent:
    def __init__(self,
                 agent_config:Agent_Config,
                 agent_max_retry=config.Agent.MAX_RETRY,
                 agent_max_error_retry=config.Agent.MAX_ERROR_RETRY
                 ):
        self.llm_config = agent_config.llm_config
        self.response_llm_client = Response_LLM_Client(self.llm_config)
        self.agent_config = agent_config

        # 自己的id
        self.agent_id = str(uuid4())
        # 多层agent体系中的顶层agent的id
        self.top_agent_id = self.agent_config.top_agent_id if self.agent_config.top_agent_id else self.agent_id

        # 经验
        self.current_exp_str = ''

        # agent最大出错次数
        self.agent_max_error_retry = agent_max_error_retry
        # agent最大次数
        self.agent_max_retry = agent_max_retry

        self.agent_status = Agent_Status()

        self.final_answer_flag = '【任务完成】'
        self.decide_final_answer_prompt = f'当完成任务时，请输出"{self.final_answer_flag}"，否则系统无法判断何时结束任务。'


    def init(self):
        self.response_llm_client.init()

    def _call_tool(self,
                   response_result:Response_Result, # response_api的调用结果
                   tool_call_paras:Tool_Call_Paras, # agent调度的上下文
                   ):
        tool_call = response_result.function_tool_call
        if tool_call and 'name' in tool_call:
            tool_name = tool_call['name']

            for func in self.response_llm_client.funcs:
                if func['name'] in tool_name:   # vllm的response api有时候会出错，如：'name': 'div_tool<|channel|>json' 而不是 'name': 'div_tool'
                # if tool_name == func['name']:
                    try:
                        args = json.loads(tool_call['arguments'])

                        # -----------------------------工具调用-----------------------------
                        # tool_call_paras.callback_tool_paras_dict = args
                        func_rtn = func['func'](tool_call_paras=tool_call_paras, **args)
                        # ----------------------------/工具调用-----------------------------

                        dprint('-----------------------------工具调用结果-------------------------------')
                        dprint(f'tool_name = "{tool_name}"')
                        dprint(func_rtn)
                        dprint('----------------------------/工具调用结果-------------------------------')
                        if isinstance(func_rtn, Action_Result):
                            response_result.tool_call_result = json.dumps(func_rtn.model_dump(), ensure_ascii=False)
                        else:
                            response_result.tool_call_result = json.dumps(func_rtn, ensure_ascii=False)

                        # tool_call_result_item = {
                        #     "type": "function_call_output",
                        #     "call_id": tool_call['call_id'],
                        #     "output": json.dumps({tool_call['name']: response_result.tool_call_result}),
                        #     "error": response_result.error
                        # }

                        self.response_llm_client.history_input_add_tool_call_result_item(call_id=tool_call['call_id'], output=json.dumps({tool_call['name']: response_result.tool_call_result}), error=response_result.error)
                        # self.response_llm_client.history_input_list.append(tool_call_result_item)

                        return response_result
                    except Exception as e:
                        response_result.error = e
                        # response_result.tool_call_result = e
                        dred(f'【Response_API_Tool_Agent._call_tool()】responses_result.error: {e!r}')
                        return response_result

        return response_result

    def _run_before(self):
        pass

    def _run_after(self):
        self.agent_status.finished = True

        # --------------------------------
        # 一轮run结束后，需要将input_list中的ResponseReasoningItem、ResponseFunctionToolCall和ResponseOutputMessage清除
        # 否则server会报validation errors for ValidatorIterator的错误
        self.response_llm_client.history_input_clear_after_this_run()

        dgreen('-----------------------------------最终结果---------------------------------------------')
        dgreen(self.agent_status.final_answer)
        dgreen('-----------------------------------最终结果---------------------------------------------')

    def run(self, query, tools):
        self._run_before()

        query_with_final_answer_flag = query + '\n' + self.decide_final_answer_prompt
        dblue(f'-------------------------------query_with_final_answer_flag-------------------------------')
        dblue(query_with_final_answer_flag)
        dblue(f'------------------------------/query_with_final_answer_flag-------------------------------')

        agent_err_count = 0
        agent_count = 0

        responses_result = Response_Result()

        while not hasattr(responses_result, 'output') or responses_result.output=='' :
            agent_count += 1
            if agent_err_count >= self.agent_max_error_retry:
                dred(f'【Response_API_Tool_Agent.run()】出错次数超出agent_max_error_retry({self.agent_max_error_retry})，退出循环.')
                break

            if agent_count >= self.agent_max_retry:
                dred(f'【Response_API_Tool_Agent.run()】调用次数超出agent_max_retry({self.agent_max_retry})，退出循环.')
                break

            response_request = Response_Request(
                instructions=query_with_final_answer_flag,  # 这里仍然是'请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'
                # input=query_with_final_answer_flag,       # 第一次请求input用query，第二次及以后的请求，input实际用了self.history_input_list
                # instructions='继续调用工具直到完成user的任务',
                model=self.llm_config.llm_model_id,
                tools=tools,

                temperature=self.llm_config.temperature,
                top_p=self.llm_config.top_p,
                max_output_tokens=self.llm_config.max_new_tokens,
                reasoning={"effort": self.llm_config.reasoning_effort},
            )

            try:
                responses_result = self.response_llm_client.responses_create(request=response_request)
            except Exception as e:
                agent_err_count += 1
                responses_result.error = e
                dred(f'【Response_API_Tool_Agent.run()】responses_result.error: {e!r}. continue')
                continue

            # tool_call_paras = None

            # 有时候没有调用工具，直接output
            if not responses_result.function_tool_call:
                # dred(f'function_tool_call为空2, responses_result.output:{responses_result.output!r}')
                if self.final_answer_flag in responses_result.output:
                    self.agent_status.final_answer = responses_result.output.replace(self.final_answer_flag, '').strip()

                    self.response_llm_client.history_input_add_output_item(self.agent_status.final_answer)
                    self._run_after()
                    return self.agent_status
                else:
                    continue

            tool_call_paras = Tool_Call_Paras(
                callback_top_agent_id=self.top_agent_id,
                callback_tool_paras_dict=json.loads(responses_result.function_tool_call['arguments']),
                callback_agent_config=self.agent_config,
                callback_agent_id=self.agent_id,
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

        self.agent_status.final_answer = responses_result.output.replace(self.final_answer_flag, '').strip()

        self.response_llm_client.history_input_add_output_item(self.agent_status.final_answer)
        self._run_after()
        return self.agent_status

def main_response_agent():
    add_tool = Tool_Request(
        name='add_tool',
        description='加法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='参数1'),
                'b': Tool_Property(type='number', description='参数2'),
                # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
        func=lambda a, b, **kwargs: {"result": a + b}
        # func=lambda a, b, unit: {"result": a + b, "unit": unit}
    )
    sub_tool = Tool_Request(
        name='sub_tool',
        description='减法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='参数1'),
                'b': Tool_Property(type='number', description='参数2'),
                # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
        func=lambda a, b, **kwargs: {"result": a - b}
        # func=lambda a, b, unit: {"result": a - b, "unit": unit}
    )
    mul_tool = Tool_Request(
        name='mul_tool',
        description='乘法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='参数1'),
                'b': Tool_Property(type='number', description='参数2'),
                # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
        func=lambda a, b, **kwargs: {"result": a * b}
        # func=lambda a, b, unit: {"result": a * b, "unit": unit}
    )
    div_tool = Tool_Request(
        name='div_tool',
        description='除法计算工具',
        parameters=Tool_Parameters(
            properties={
                'a': Tool_Property(type='number', description='参数1'),
                'b': Tool_Property(type='number', description='参数2'),
                # 'unit': Tool_Property(type='string', description='单位', enum=['meter', 'kilo-miter']),
            },
            required=['a', 'b'],
        ),
        func=lambda a, b, **kwargs: {"result": a / b}
        # func=lambda a, b, unit: {"result": a / b, "unit": unit}
    )

    from agent.tools.folder_tool import Folder_Tool
    fold_tool = Folder_Tool.get_tool_param_dict()

    tools = [fold_tool, add_tool, sub_tool, mul_tool, div_tool]

    agent_config = Agent_Config(
        agent_name = 'agent for search folder',
        tool_names=['Folder_Tool'],
        # llm_config=llm_protocol.g_local_qwen3_30b_thinking,
        llm_config=llm_protocol.g_online_groq_gpt_oss_20b,
        # llm_config=llm_protocol.g_online_groq_gpt_oss_120b,
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4,
        has_history=True,
    )

    query = '请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，搜索所有子文件夹直到找到'
    # query = '请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'
    # query = '你是谁？'

    agent = Response_API_Tool_Agent(agent_config=agent_config)
    agent.init()
    # agent.run(query=query, tools=tools)
    # agent.run(query='你好，我的名字是土土', tools=tools)
    agent.run(query=query, tools=tools)
    # agent.run(query='你还记得我的名字是什么吗？还有之前file_to_find.txt在哪里找到的来着？', tools=tools)

if __name__ == "__main__":
    main_response_agent()