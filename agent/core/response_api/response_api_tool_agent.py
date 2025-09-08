
import llm_protocol
from llm_protocol import LLM_Config
from agent.tools.protocol import Tool_Call_Paras
from tools.llm.response_api_client import Response_LLM_Client, Response_Result, Tool_Request, Tool_Parameters, Tool_Property, Response_Request

from agent.core.protocol import Query_Agent_Context
from agent.tools.protocol import Tool_Call_Paras

from config import dred, dgreen, dblue, dyellow, dcyan

class Response_API_Tool_Agent:
    def __init__(self, llm_config:LLM_Config):
        self.llm_config = llm_config
        self.response_llm_client = Response_LLM_Client(self.llm_config)

    def init(self):
        self.response_llm_client.init()

    def _call_tool(self,
                   response_result:Response_Result, # response_api的调用结果
                   tool_call_paras:Tool_Call_Paras, # agent调度的上下文
                   ):
        pass

    def run(self, query, tools):
        response_request = Response_Request(
            model=self.llm_config.llm_model_id,
            input=query,
            tools=tools,
        )
        responses_result = self.response_llm_client.responses_create(request=response_request)
        responses_result = self.response_llm_client.legacy_call_tool(responses_result)

        while not hasattr(responses_result, 'output') or responses_result.output=='' :
            response_request = Response_Request(
                instructions=query,  # 这里仍然是'请告诉我2356/3567+22*33+3567/8769+4356/5678等于多少，保留10位小数，要调用工具计算，不能直接心算'
                # instructions='继续调用工具直到完成user的任务',
                model=self.llm_config.llm_model_id,
                tools=tools,
            )
            responses_result = self.response_llm_client.responses_create(request=response_request)
            responses_result = self.response_llm_client.legacy_call_tool(responses_result)

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

    agent = Response_API_Tool_Agent(llm_config=llm_protocol.g_online_groq_gpt_oss_20b)
    agent.init()
    agent.run(query=query, tools=tools)

if __name__ == "__main__":
    main_response_agent()
