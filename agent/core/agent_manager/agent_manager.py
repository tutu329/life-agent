from typing import Any, Dict, List, Literal, Optional, Union, Tuple, TYPE_CHECKING
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

    # 创建agent，返回agent_id
    @classmethod
    def create_agent(cls, agent_config:Agent_Config)->str:
        tool_objects = []

        # 根据MCP url，添加allowed对应的tools
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

    # 根据agent_id，获取agent对象
    @classmethod
    def _get_agent(cls, agent_id:str)->Toolcall_Agent:
        return cls.agents_dict.get(agent_id)

    # 运行agent_id对应的对象
    @classmethod
    def run_agent(cls, agent_id:str, query):
        agent = cls._get_agent(agent_id)
        agent.run(query=query)

    # 获取MCP url对应的tools列表
    @classmethod
    def get_mcp_url_tool_names(cls, mcp_url:str)->List[str]:
        return get_mcp_server_tool_names(server_url=mcp_url)

    # 获取某agent的所有local和MCP的tool names
    @classmethod
    def get_all_tool_names(cls, agent_id) -> List[str]:
        agent = cls._get_agent(agent_id)
        return agent.agent_config.tool_names

def main():
    from agent.tools.folder_tool import Folder_Tool
    fold_tool = Folder_Tool.get_tool_param_dict()

    dprint("--------------MCP------------------")
    dpprint(Agent_Manager.get_mcp_url_tool_names("https://powerai.cc:8011/mcp/sqlite/sse"))
    dpprint(Agent_Manager.get_mcp_url_tool_names("http://localhost:8789/sse"))
    dprint("-------------/MCP------------------")

    mcp_requests = [
        MCP_Server_Request(url="https://powerai.cc:8011/mcp/sqlite/sse", allowed_tool_names=['list_tables', 'read_query']),
        MCP_Server_Request(url="http://localhost:8789/sse", allowed_tool_names=['tavily-search']),
    ]

    agent_config = Agent_Config(
        llm_config=llm_protocol.g_local_gpt_oss_120b_mxfp4_lmstudio,
        agent_name='Agent created by Agent_Manager',
        tool_names=['Folder_Tool'],
        # tool_names=['read_query', 'write_query', 'create_table', 'list_tables', 'describe_table', 'append_insight', 'tavily-search', 'tavily-extract', 'tavily-crawl', 'tavily-map'],
        tool_objects=[fold_tool],
        mcp_requests=mcp_requests,
        has_history=True,
    )
    # dprint("--------------agent_config------------------")
    # dpprint(agent_config.model_dump())
    # dprint("-------------/agent_config------------------")

    agent_id = Agent_Manager.create_agent(agent_config)

    dprint("--------------注册后tool情况------------------")
    dprint(Agent_Manager.get_all_tool_names(agent_id))
    dprint("-------------/注册后tool情况------------------")

    Agent_Manager.run_agent(agent_id=agent_id, query='有哪些表格？')
    Agent_Manager.run_agent(agent_id=agent_id, query='通信录表里有哪些数据？')

if __name__ == "__main__":
    main()
