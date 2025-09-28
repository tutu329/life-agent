from pprint import pprint

from agent.core.mcp.mcp_manager import get_mcp_server_tools, get_mcp_server_tool_names
from agent.core.agent_config import Agent_Config
from agent.core.toolcall_agent import Toolcall_Agent
from agent.tools.protocol import Tool_Request

import llm_protocol

import config

DEBUG = True
# DEBUG = config.Global.app_debug

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def dpprint(*args, **kwargs):
    if DEBUG:
        pprint(*args, **kwargs)

g_agent_dict = {} # agent_id <--> agent object

# agent工厂
class Agent_Manager:
    agents_dict = {}

    @classmethod
    def create_agent(cls, agent_config:Agent_Config)->str:
        tool_objects = []

        # 处理MCP tool objects
        if agent_config.mcp_urls:
            for mcp_url in agent_config.mcp_urls:
                dprint(f'mcp_url: {mcp_url!r}')
                tool_objects += get_mcp_server_tools(mcp_url)
        agent_config.tool_objects = tool_objects

        # agent初始化
        agent = Toolcall_Agent(agent_config=agent_config)
        agent.init()

        # 注册agent
        cls.agents_dict[agent.agent_id] = agent

        # 返回agent id
        return agent.agent_id

    @classmethod
    def get_agent(cls, agent_id:str)->Toolcall_Agent:
        return cls.agents_dict.get(agent_id)

    @classmethod
    def run_agent(cls, agent_id:str, query):
        agent = cls.get_agent(agent_id)
        agent.run(query=query)

def main():
    agent_config = Agent_Config(
        llm_config=llm_protocol.g_local_gpt_oss_120b_mxfp4_lmstudio,
        agent_name='Agent created by Agent_Manager',
        tool_names=['read_query', 'write_query', 'create_table', 'list_tables', 'describe_table', 'append_insight', 'tavily-search', 'tavily-extract', 'tavily-crawl', 'tavily-map'],
        tool_objects=[],
        mcp_urls=[
            "https://powerai.cc:8011/mcp/sqlite/sse",
            "http://localhost:8789/sse"
        ],
        has_history=True,
    )
    dprint("--------------agent_config------------------")
    # dpprint(agent_config.model_dump())
    dprint("-------------/agent_config------------------")

    agent_id = Agent_Manager.create_agent(agent_config)
    Agent_Manager.run_agent(agent_id=agent_id, query='有哪些表格？')
    Agent_Manager.run_agent(agent_id=agent_id, query='通信录表里有哪些数据？')

def main1():
    from openai import OpenAI
    import httpx
    import llm_protocol
    import config

    server_url1 = "https://powerai.cc:8011/mcp/sqlite/sse"
    server_url2 = "http://localhost:8789/sse"
    # server_url = "https://powerai.cc:8011/mcp/everything/sse"
    tools = get_mcp_server_tools(server_url1) +  get_mcp_server_tools(server_url2)
    tool_names = get_mcp_server_tool_names(server_url1) + get_mcp_server_tool_names(server_url2)
    print(tool_names)
    # print(tools)
    # for tool in tools:
    #     print(tool)

    agent_config = Agent_Config(
        agent_name='MCP agent',
        tool_names=tool_names,
        tool_objects=tools,
        # llm_config=llm_protocol.g_online_groq_gpt_oss_20b,
        # llm_config=llm_protocol.g_online_groq_gpt_oss_120b,
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4,
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4_lmstudio,
        # llm_config=llm_protocol.g_online_qwen3_next_80b_instruct,
        # llm_config=llm_protocol.g_online_qwen3_next_80b_thinking,
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4,
        llm_config=llm_protocol.g_local_gpt_oss_120b_mxfp4_lmstudio,
        # llm_config=llm_protocol.g_local_qwen3_30b_gptq_int4,
        has_history=True,
    )
    agent = Toolcall_Agent(agent_config=agent_config)
    agent.init()
    # agent.run(query='列出所有表格名称', tools=tools)
    # agent.run(query='查看通信录表的数据', tools=tools)

    while True:
        agent.run(query=input('请输入你的指令：'))

if __name__ == "__main__":
    main()
    # main1()