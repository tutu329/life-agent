import os
import importlib.util
import inspect

from typing import Any, Dict, List, Literal, Optional, Union, Tuple, TYPE_CHECKING
from pprint import pprint
from threading import Thread

from agent.core.mcp.mcp_manager import get_mcp_server_tools, get_mcp_server_tool_names
from agent.core.agent_config import Agent_Config
from agent.core.toolcall_agent import Toolcall_Agent
from agent.tools.protocol import Tool_Request, Tool_Parameters, Tool_Property, Property_Type, get_tool_param_dict_from_tool_class
from agent.core.mcp.protocol import MCP_Server_Request
from agent.core.protocol import Agent_Status, Agent_Data

from agent.tools.tool_manager import server_register_all_local_tool_on_start

import llm_protocol

import config
from config import dred,dgreen,dcyan,dyellow,dblue,dblack,dwhite

DEBUG = True
# DEBUG = config.Global.app_debug

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def dpprint(*args, **kwargs):
    if DEBUG:
        pprint(*args, **kwargs)

# agent工厂
class Agent_Manager:
    agents_dict: Dict[str, Agent_Data]          = {}    # 用于注册全server所有的agents, agent_id <--> agent_data
    local_tool_objects_list: List[Tool_Request] = []    # 用于存放server本地的所有tools

    # 0、用于server管理时的唯一的、必需的启动
    @classmethod
    def _on_server_start(cls)->List[Dict[str, Any]]: # 由server侧调用
        cls.local_tool_objects_list = Agent_Manager.parse_all_local_tools_on_server_start()
        return cls.local_tool_objects_list

    # 1、创建agent，返回agent_id
    @classmethod
    def create_agent(cls, agent_config:Agent_Config)->str:

        # 获取所有的local tools
        allowd_local_tools = []
        for tool in cls.local_tool_objects_list:
            if tool.name in agent_config.allowed_local_tool_names:
                allowd_local_tools.append(tool)

        allowed_mcp_tools = []
        # 根据MCP url，添加allowed对应的tools
        if agent_config.mcp_requests:
            for mcp_req in agent_config.mcp_requests:
                dprint(f'mcp_url: {mcp_req.url!r}')
                allowed_mcp_tools += get_mcp_server_tools(mcp_req.url, allowed_tools=mcp_req.allowed_tool_names)

        # 已有tools加上MCP的tools
        if agent_config.tool_objects is None:
            agent_config.tool_objects = []
        agent_config.tool_objects = allowd_local_tools + allowed_mcp_tools

        # agent初始化
        agent = Toolcall_Agent(agent_config=agent_config)
        agent.init()

        # 注册agent
        agent_data = Agent_Data(
            agent_id=agent.agent_id,
            agent=agent,
        )
        cls.agents_dict[agent.agent_id] = agent_data

        # 返回agent id
        return agent.agent_id

    # 2、启动agent_id下的thread，并run
    @classmethod
    def run_agent(cls, agent_id:str, query):
        agent_data = cls.agents_dict[agent_id]
        agent = cls._get_agent(agent_id=agent_id)

        def _worker(query):
            agent.run(query=query)

        # 启动agent的thread
        agent_data.agent_thread = Thread(
            target=_worker,
            args=(query,),
        )
        agent_data.agent_thread.start()


    # 根据agent_id，获取agent对象
    @classmethod
    def _get_agent(cls, agent_id:str)->Toolcall_Agent:
        agent_data = cls.agents_dict.get(agent_id)
        return agent_data.agent

    # 获取MCP url对应的tools列表
    @classmethod
    def get_mcp_url_tool_names(cls, mcp_url:str)->List[str]:
        return get_mcp_server_tool_names(server_url=mcp_url)

    @classmethod
    def get_local_tool_names(cls)->List[str]:
        local_tool_names = []
        for tool in cls.local_tool_objects_list:
            local_tool_names.append(tool.name)
        return local_tool_names

    @classmethod
    def get_local_tool_param_dict(cls, tool_name)->Tool_Request:
        if cls.local_tool_objects_list:
            for tool in cls.local_tool_objects_list:
                if tool_name==tool.name:
                    return tool
        return None

    # 获取某agent的所有local和MCP的tool names
    @classmethod
    def _get_all_tool_debug_info_list(cls, agent_id) -> List[str]:
        tool_info_list = []
        agent = cls._get_agent(agent_id)
        for tool in agent.agent_config.tool_objects:
            tool_info_list.append({
                'name': tool.name,
                'parameters': tool.parameters,
                # 'description': tool.description,
            })
        return tool_info_list

    @classmethod
    def parse_all_local_tools_on_server_start(cls) -> List[Dict[str, Any]]:
        """
        获取 life-agent.agent.tools 文件夹下所有 py 文件里的 tool 信息

        Returns:
            List[Dict]: 包含所有 tool 信息的列表，每个元素包含：
                - name: tool 名称
                - description: tool 描述
                - parameters: tool 参数
                - tool_class: tool 类对象（非实例）
        """
        tool_param_dict_list = []
        tools_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools')
        dprint(f'--------------tools_dir----------------')
        dprint(tools_dir)
        dprint(f'-------------/tools_dir----------------')

        tool_param_list = []
        # 遍历 tools 文件夹下的所有 py 文件
        for filename in os.listdir(tools_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = filename[:-3]  # 去掉 .py 后缀
                file_path = os.path.join(tools_dir, filename)

                try:
                    # 动态导入模块
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # 查找模块中的类
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        # 检查是否是在当前模块中定义的类（不是导入的类）
                        if (obj.__module__ == module_name and
                                hasattr(obj, 'tool_name') and
                                hasattr(obj, 'tool_description') and
                                hasattr(obj, 'tool_parameters')):

                            if 'required' in obj.tool_parameters:
                                required_field_in_parameter = False
                            else:
                                required_field_in_parameter = True

                            tool_param = get_tool_param_dict_from_tool_class(obj, required_field_in_parameter)
                            tool_param_list.append(tool_param)

                except Exception as e:
                    dyellow(f"【Agent_Manager.server_init_local_tools_on_start】warning: 尝试动态导入 {filename} 失败: {e!r}")
                    continue

        return tool_param_list

def main():
    # from agent.tools.folder_tool import Folder_Tool
    # fold_tool = Folder_Tool.get_tool_param_dict()

    # tool_list = Agent_Manager.parse_all_local_tools_on_server_start()
    local_tool_list = Agent_Manager._on_server_start()
    dprint("--------------tools_info------------------")
    for tool_param_dict in local_tool_list:
        dprint(tool_param_dict)
    dprint("-------------/tools_info------------------")

    dprint("--------------client_get_server_local_tools_info------------------")
    dprint(Agent_Manager.get_local_tool_names())
    dprint(Agent_Manager.get_local_tool_param_dict(tool_name='Write_Chapter_Tool'))
    dprint(Agent_Manager.get_local_tool_param_dict(tool_name='Folder_Tool'))
    dprint("--------------client_get_server_local_tools_info------------------")



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
        allowed_local_tool_names=['Folder_Tool'],
        # allowed_local_tool_names=['Folder_Tool', 'Write_Chapter_Tool'],
        # allowed_local_tool_names=['Write_Chapter_Tool'],
        # tool_names=['Folder_Tool'],
        # tool_names=['read_query', 'write_query', 'create_table', 'list_tables', 'describe_table', 'append_insight', 'tavily-search', 'tavily-extract', 'tavily-crawl', 'tavily-map'],
        # tool_objects=tool_list,
        # tool_objects=[fold_tool],
        mcp_requests=mcp_requests,
        has_history=True,
    )
    # dprint("--------------agent_config------------------")
    # dpprint(agent_config.model_dump())
    # dprint("-------------/agent_config------------------")

    agent_id = Agent_Manager.create_agent(agent_config)

    dprint("--------------注册后tool情况------------------")
    for info in Agent_Manager._get_all_tool_debug_info_list(agent_id):
        dprint(info)
    dprint("-------------/注册后tool情况------------------")

    Agent_Manager.run_agent(agent_id=agent_id, query='请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，需要遍历每一个子文件夹，一定能找到')
    # Agent_Manager.run_agent(agent_id=agent_id, query='请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，递归搜索所有子文件夹直到准确找到该文件')
    # Agent_Manager.run_agent(agent_id=agent_id, query='有哪些表格？')
    # Agent_Manager.run_agent(agent_id=agent_id, query='通信录表里有哪些数据？')

if __name__ == "__main__":
    main()