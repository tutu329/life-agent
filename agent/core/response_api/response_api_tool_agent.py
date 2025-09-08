
import llm_protocol
from llm_protocol import LLM_Config
from agent.tools.protocol import Tool_Call_Paras
from tools.llm.response_api_client import Response_LLM_Client, Response_Result, Tool_Request, Tool_Parameters, Tool_Property, Response_Request

from agent.core.protocol import Query_Agent_Context
from agent.tools.protocol import Tool_Call_Paras

from config import dred, dgreen, dblue, dyellow, dcyan
from pprint import pprint
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
    def __init__(self, llm_config:LLM_Config):
        self.llm_config = llm_config
        self.response_llm_client = Response_LLM_Client(self.llm_config)

        self.top_agent_id = None
        self.agent_config = None
        self.agent_id = None
        self.current_exp_str = None

    def init(self):
        self.response_llm_client.init()

    def _call_tool(self,
                   response_result:Response_Result, # response_api的调用结果
                   tool_call_paras:Tool_Call_Paras, # agent调度的上下文
                   ):
        tool_call = response_result.function_tool_call
        if tool_call and 'name' in tool_call:
            tool_name = tool_call['name']
            dprint(f'tool_name = "{tool_name}"')

            for func in self.response_llm_client.funcs:
                if tool_name == func['name']:
                    args = json.loads(tool_call['arguments'])

                    func_rtn = func['func'](**args)
                    response_result.tool_call_result = json.dumps(func_rtn, ensure_ascii=False)

                    tool_call_result_item = {
                        "type": "function_call_output",
                        "call_id": tool_call['call_id'],
                        "output": json.dumps({tool_call['name']: response_result.tool_call_result})
                    }

                    self.response_llm_client.history_input_list.append(tool_call_result_item)

                    return response_result

        return response_result

    def run(self, query, tools):
        response_request = Response_Request(
            model=self.llm_config.llm_model_id,
            input=query,
            tools=tools,
        )
        responses_result = self.response_llm_client.responses_create(request=response_request)

        tool_call_paras = None
        # tool_call_paras = Tool_Call_Paras(
        #     callback_top_agent_id=self.top_agent_id,
        #     callback_tool_paras_dict=responses_result.function_tool_call['arguments'],
        #     callback_agent_config=self.agent_config,
        #     callback_agent_id=self.agent_id,
        #     # callback_last_tool_ctx=last_tool_ctx,
        #     # callback_client_ctx=context,
        #     callback_father_agent_exp=self.current_exp_str
        # )
        responses_result = self._call_tool(responses_result, tool_call_paras)
        # responses_result = self.response_llm_client.legacy_call_tool(responses_result)

        while not hasattr(responses_result, 'output') or responses_result.output=='' :
            response_request = Response_Request(
                instructions=query,  # 这里仍然是'请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'
                # instructions='继续调用工具直到完成user的任务',
                model=self.llm_config.llm_model_id,
                tools=tools,
            )
            responses_result = self.response_llm_client.responses_create(request=response_request)

            tool_call_paras = None
            # tool_call_paras = Tool_Call_Paras(
            #     callback_top_agent_id=self.top_agent_id,
            #     callback_tool_paras_dict=responses_result.function_tool_call['arguments'],
            #     callback_agent_config=self.agent_config,
            #     callback_agent_id=self.agent_id,
            #     # callback_last_tool_ctx=last_tool_ctx,
            #     # callback_client_ctx=context,
            #     callback_father_agent_exp=self.current_exp_str
            # )
            responses_result = self._call_tool(responses_result, tool_call_paras)
            # responses_result = self.response_llm_client.legacy_call_tool(responses_result)

            if responses_result is None:
                continue

            if responses_result.output != '':
                dgreen('-----------------------------------最终结果---------------------------------------------')
                dgreen(responses_result.output)
                dgreen('-----------------------------------最终结果---------------------------------------------')
                break

        return responses_result.output

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

    tools = [add_tool, sub_tool, mul_tool, div_tool]

    query = '请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'

    agent = Response_API_Tool_Agent(llm_config=llm_protocol.g_online_groq_gpt_oss_120b)
    # agent = Response_API_Tool_Agent(llm_config=llm_protocol.g_online_groq_gpt_oss_20b)
    agent.init()
    agent.run(query=query, tools=tools)

if __name__ == "__main__":
    main_response_agent()
