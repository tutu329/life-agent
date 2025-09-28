from pprint import pprint

from agent.core.mcp.mcp_manager import get_mcp_server_tools, get_mcp_server_tool_names
from agent.core.agent_config import Agent_Config
from agent.core.toolcall_agent import Toolcall_Agent
from agent.tools.protocol import Tool_Request
from agent.core.mcp.protocol import MCP_Server_Request

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
        if agent_config.mcp_requests:
            for mcp_req in agent_config.mcp_requests:
                dprint(f'mcp_url: {mcp_req.url!r}')
                tool_objects += get_mcp_server_tools(mcp_req.url, allowed_tools=mcp_req.allowed_tool_names)
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
    mcp_requests = [
        MCP_Server_Request(url="https://powerai.cc:8011/mcp/sqlite/sse", allowed_tool_names=['list_tables', 'read_query']),
        MCP_Server_Request(url="http://localhost:8789/sse", allowed_tool_names=['tavily-search']),
    ]
    agent_config = Agent_Config(
        llm_config=llm_protocol.g_local_gpt_oss_120b_mxfp4_lmstudio,
        agent_name='Agent created by Agent_Manager',
        # tool_names=['list_tables'],
        # tool_names=['read_query', 'write_query', 'create_table', 'list_tables', 'describe_table', 'append_insight', 'tavily-search', 'tavily-extract', 'tavily-crawl', 'tavily-map'],
        tool_objects=[],
        mcp_requests=mcp_requests,
        has_history=True,
    )
    dprint("--------------agent_config------------------")
    # dpprint(agent_config.model_dump())
    dprint("-------------/agent_config------------------")

    agent_id = Agent_Manager.create_agent(agent_config)
    Agent_Manager.run_agent(agent_id=agent_id, query='有哪些表格？')
    Agent_Manager.run_agent(agent_id=agent_id, query='通信录表里有哪些数据？')

if __name__ == "__main__":
    main()
