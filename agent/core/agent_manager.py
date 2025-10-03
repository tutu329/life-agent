import os, time
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
from agent.core.protocol import Agent_Status, Agent_Data, Agent_Request_Result_Type, Agent_Phase, Query_Agent_Context, Agent_Request_Result, Agent_Request_Result_Type, Agent_Phase

from agent.tools.tool_manager import server_register_all_local_tool_on_start
from console import err

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
    local_all_tool_requests: List[Tool_Request] = []    # 用于存放server本地的所有tool_requests

    # 0、用于server管理时的唯一的、必需的启动
    @classmethod
    def _on_server_start(cls)->List[Dict[str, Any]]: # 由server侧调用
        cls.local_all_tool_requests = Agent_Manager.parse_all_local_tools_on_server_start()
        return cls.local_all_tool_requests

    # 获取cls.agents_dict中所有的agents as tool，返回list
    @classmethod
    def get_all_agents_as_tool(cls)->List[Agent_Data]:
        agent_data_list = []
        dred('------------------get_all_agents_as_tool---------------------')
        for agent_id, agent_data in cls.agents_dict.items():
            if agent_data.agent.agent_config.as_tool_name:
                agent_data_list.append(agent_data)
                dred(f'tool_name: {agent_data.agent.agent_config.as_tool_name!r}, tool_description: {agent_data.agent.agent_config.as_tool_description!r}')
        dred('-----------------/get_all_agents_as_tool---------------------')
        return agent_data_list

    # 1、创建agent，返回agent_id
    @classmethod
    def create_agent(cls, agent_config:Agent_Config)->str:
        result = Agent_Request_Result(
            agent_id='',
            phase=Agent_Phase.CREATING,
            result_type=Agent_Request_Result_Type.SUCCESS,
        )

        allowd_local_tool_requests = []
        allowed_mcp_tool_requests = []

        try:
            # 获取所有的local tools
            if agent_config.allowed_local_tool_names:
                # --------------获取所有的普通local tools--------------
                for local_tool_request in cls.local_all_tool_requests:
                    if local_tool_request.name in agent_config.allowed_local_tool_names:
                        allowd_local_tool_requests.append(local_tool_request)
                # -------------/获取所有的普通local tools--------------

                # -----------获取所有的local agent as tools-----------
                for agent_as_tool in cls.get_all_agents_as_tool():
                    if agent_as_tool.agent.agent_config.as_tool_name in agent_config.allowed_local_tool_names:
                        agent_as_tool_parameters = Tool_Parameters(
                            properties={'query': Tool_Property(type="string", description='交给该tool(该tool同时是一个agent)的指令')},  # 这里参数必须是toolcall_agent.run(self, query)的query
                            required=['query'],
                        )
                        agent_as_tool_request = Tool_Request(
                            name=agent_as_tool.agent.agent_config.as_tool_name,
                            description=agent_as_tool.agent.agent_config.as_tool_description,
                            parameters=agent_as_tool_parameters,
                            # func=agent_as_tool.agent.run,   # 注意这里是一个agent的成员函数run(self, query)，而python中，只要这里的func注册的是绑定对象如agent_obj.run()，后续回调就不需要输入self，如果是注册的是未绑定对象的如Toolcall_Agent.run，则回调需要输入self。（但是：obj或者obj.func存在pydantic中时，deepcopy都会报错）
                            func=Toolcall_Agent.run,   # 注意这里是一个agent的成员函数run(self, query)，而python中，只要这里的func注册的是绑定对象如agent_obj.run()，后续回调就不需要输入self，如果是注册的是未绑定对象的如Toolcall_Agent.run，则回调需要输入self。（但是：obj或者obj.func存在pydantic中时，deepcopy都会报错）
                        )
                        allowd_local_tool_requests.append(agent_as_tool_request)
                # ----------/获取所有的local agent as tools-----------

            # 根据MCP url，添加allowed对应的tools
            if agent_config.mcp_requests:
                # --------------获取所有的MCP tools--------------
                for mcp_req in agent_config.mcp_requests:
                    dprint(f'mcp_url: {mcp_req.url!r}')
                    allowed_mcp_tool_requests += get_mcp_server_tools(mcp_req.url, allowed_tools=mcp_req.allowed_tool_names)
                # -------------、获取所有的MCP tools--------------

            # 整理所有tool的requests
            if agent_config.all_tool_requests is None:
                agent_config.all_tool_requests = []
            agent_config.all_tool_requests = allowd_local_tool_requests + allowed_mcp_tool_requests

        except Exception as e:
            err(e)
            result.result_type = Agent_Request_Result_Type.FAILED
            result.result_content = str(e)
            return result

        # agent初始化
        agent = Toolcall_Agent(agent_config=agent_config)
        agent.init()

        # 注册agent
        agent_data = Agent_Data(
            agent_id=agent.agent_id,
            agent=agent,
        )
        cls.agents_dict[agent.agent_id] = agent_data

        result.agent_id = agent.agent_id

        dprint()
        dprint('--------------agent request result--------------')
        dprint(result)
        dprint('-------------/agent request result--------------')
        return result

    # 2、启动agent_id下的thread，并run
    @classmethod
    def run_agent(cls, agent_id:str, query):
        result = Agent_Request_Result(
            agent_id=agent_id,
            phase=Agent_Phase.RUNNING,
            result_type=Agent_Request_Result_Type.SUCCESS,
        )

        agent_data = cls.agents_dict[agent_id]
        agent = cls._get_agent(agent_id=agent_id)

        if agent.agent_status.querying:
            result.result_type = Agent_Request_Result_Type.FAILED
            result.result_content = f'agent "{agent_id}" is still querying.'
            return result

        def _worker(query):
            agent.run(query=query)

        # 启动agent的thread
        agent_data.agent_thread = Thread(
            target=_worker,
            args=(query,),
        )
        agent_data.agent_thread.start()

        dprint()
        dprint('--------------agent request result--------------')
        dprint(result)
        dprint('-------------/agent request result--------------')
        return result

    # 3、等待agent的某次query(串行，暂不考虑并行和query_id)
    @classmethod
    def wait_agent(cls, agent_id):
        thread = cls._get_thread(agent_id=agent_id)
        thread.join()

    # 4、获取agent的实时状态
    @classmethod
    def get_agent_status(cls, agent_id)->Agent_Status:
        agent_data = cls.agents_dict[agent_id]
        return agent_data.agent.agent_status

    # 根据agent_id，获取agent对象
    @classmethod
    def _get_agent(cls, agent_id:str)->Toolcall_Agent:
        agent_data = cls.agents_dict.get(agent_id)
        return agent_data.agent

    # 根据agent_id，获取thread
    @classmethod
    def _get_thread(cls, agent_id:str)->Thread:
        agent_data = cls.agents_dict.get(agent_id)
        return agent_data.agent_thread

    # 获取MCP url对应的tools列表
    @classmethod
    def get_mcp_url_tool_names(cls, mcp_url:str)->List[str]:
        return get_mcp_server_tool_names(server_url=mcp_url)

    @classmethod
    def get_local_tool_names(cls)->List[str]:
        local_tool_names = []
        for tool in cls.local_all_tool_requests:
            local_tool_names.append(tool.name)
        return local_tool_names

    @classmethod
    def get_local_tool_param_dict(cls, tool_name)->Tool_Request:
        if cls.local_all_tool_requests:
            for tool in cls.local_all_tool_requests:
                if tool_name==tool.name:
                    return tool
        return None

    # 获取某agent的所有local和MCP的tool names
    @classmethod
    def _get_all_tool_debug_info_list(cls, agent_id) -> List[str]:
        tool_info_list = []
        agent = cls._get_agent(agent_id)
        for tool in agent.agent_config.all_tool_requests:
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

def main_one_agent():
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

    agent_id = Agent_Manager.create_agent(agent_config).agent_id

    dprint("--------------注册后tool情况------------------")
    for info in Agent_Manager._get_all_tool_debug_info_list(agent_id):
        dprint(info)
    dprint("-------------/注册后tool情况------------------")

    res = Agent_Manager.run_agent(agent_id=agent_id, query='请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，需要遍历每一个子文件夹，一定能找到')
    # Agent_Manager.wait_agent(agent_id=agent_id)

    while True:
        res = Agent_Manager.run_agent(agent_id=agent_id, query='你刚才搜索file_to_find.txt这个文件的位置的结果是啥来着')
        if res.result_type==Agent_Request_Result_Type.SUCCESS:
            break
        time.sleep(0.1)

    # Agent_Manager.wait_agent(agent_id=agent_id)


    # Agent_Manager.run_agent(agent_id=agent_id, query='请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，递归搜索所有子文件夹直到准确找到该文件')
    # Agent_Manager.run_agent(agent_id=agent_id, query='有哪些表格？')
    # Agent_Manager.run_agent(agent_id=agent_id, query='通信录表里有哪些数据？')

def main_2_levels_agents():
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

    # -----------------------------注册一个agent as tool-----------------------------------
    agent_config = Agent_Config(
        llm_config=llm_protocol.g_local_gpt_oss_120b_mxfp4_lmstudio,
        agent_name='这是一个专门回答理论物理问题的Agent',
        as_tool_name='Physical_Problems_Solving_Tool',
        as_tool_description='本工具用来回答理论物理问题',
    )
    res = Agent_Manager.create_agent(agent_config)
    # ----------------------------/注册一个agent as tool-----------------------------------

    agent_config = Agent_Config(
        # llm_config=llm_protocol.g_online_deepseek_chat,
        # llm_config=llm_protocol.g_online_groq_gpt_oss_120b,
        llm_config=llm_protocol.g_local_gpt_oss_120b_mxfp4_lmstudio,
        agent_name='Agent created by Agent_Manager',
        allowed_local_tool_names=['Folder_Tool', 'Physical_Problems_Solving_Tool'],
        # allowed_local_tool_names=['Folder_Tool', 'Write_Chapter_Tool'],
        # allowed_local_tool_names=['Write_Chapter_Tool'],
        # tool_names=['Folder_Tool'],
        # tool_names=['read_query', 'write_query', 'create_table', 'list_tables', 'describe_table', 'append_insight', 'tavily-search', 'tavily-extract', 'tavily-crawl', 'tavily-map'],
        # tool_objects=tool_list,
        # tool_objects=[fold_tool],
        # mcp_requests=mcp_requests,
        # has_history=True,
    )
    # dprint("--------------agent_config------------------")
    # dpprint(agent_config.model_dump())
    # dprint("-------------/agent_config------------------")

    res = Agent_Manager.create_agent(agent_config)
    dprint()
    dprint('--------------agent request result--------------')
    dprint(res)
    dprint('-------------/agent request result--------------')
    agent_id = res.agent_id

    dprint("--------------注册后tool情况------------------")
    for info in Agent_Manager._get_all_tool_debug_info_list(agent_id):
        dprint(info)
    dprint("-------------/注册后tool情况------------------")

    res = Agent_Manager.run_agent(agent_id=agent_id, query='请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，需要遍历每一个子文件夹，一定能找到')
    # Agent_Manager.wait_agent(agent_id=agent_id)

    while True:
        res = Agent_Manager.run_agent(agent_id=agent_id, query='你刚才搜索file_to_find.txt这个文件的位置的结果是啥来着')
        if res.result_type==Agent_Request_Result_Type.SUCCESS:
            break
        time.sleep(0.1)

    # Agent_Manager.wait_agent(agent_id=agent_id)


    # Agent_Manager.run_agent(agent_id=agent_id, query='请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，递归搜索所有子文件夹直到准确找到该文件')
    # Agent_Manager.run_agent(agent_id=agent_id, query='有哪些表格？')
    # Agent_Manager.run_agent(agent_id=agent_id, query='通信录表里有哪些数据？')

if __name__ == "__main__":
    # main_one_agent()
    main_2_levels_agents()