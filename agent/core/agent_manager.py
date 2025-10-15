import os, time, copy
import importlib.util
import inspect

from typing import Any, Dict, List, Set, Literal, Optional, Union, Tuple, TYPE_CHECKING, Callable
from pprint import pprint
from threading import Thread

from agent.core.mcp.mcp_manager import get_mcp_server_tools, get_mcp_server_tool_names, get_mcp_server_tool_names_async
from agent.core.agent_config import Agent_Config
from agent.core.toolcall_agent import Toolcall_Agent
from agent.tools.protocol import Tool_Request, Tool_Parameters, Tool_Property, Property_Type, get_tool_request_from_tool_class, get_tool_request_and_func_from_tool_class
from agent.core.mcp.protocol import MCP_Server_Request
from agent.core.protocol import Agent_Status, Agent_Data, Agent_Request_Result_Type, Agent_Request_Type, Query_Agent_Context, Agent_Request_Result, Agent_Request_Result_Type, Agent_Request_Type
from agent.core.resource.protocol import Resource_Data
from agent.core.resource.redis_resource_manager import Redis_Resource_Manager
from web_socket_server import Web_Socket_Server_Manager

from agent.tools.tool_manager import server_register_all_local_tool_on_start
from console import err, server_output

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
    local_all_tool_funcs: List[Callable] = []

    web_socket_server:Web_Socket_Server_Manager = None

    # 0、用于server管理时的唯一的、必需的启动
    @classmethod
    def init(cls)->Tuple[List[Tool_Request], List[Callable]]: # 由server侧调用
    # def get_local_tool_requests_and_funcs_on_server_start(cls)->Tuple[List[Tool_Request], List[Callable]]: # 由server侧调用

        # 初始化local tools
        cls.local_all_tool_requests, cls.local_all_tool_funcs = Agent_Manager.parse_all_local_tools_on_server_start()

        # 初始化ws server
        cls.web_socket_server = Web_Socket_Server_Manager.start_server(config.Port.global_web_socket_server, server_at="agent_manager.py")

        return cls.local_all_tool_requests, cls.local_all_tool_funcs

    # 返回tool的name、description、parameters
    @classmethod
    def get_local_all_tool_info_json(cls)->List[Tool_Request]:
        rtn_tool_requests = copy.deepcopy(cls.local_all_tool_requests)
        rtn_list = []
        for rtn_tool_request in rtn_tool_requests:
            del rtn_tool_request.type
            del rtn_tool_request.strict
            rtn_list.append(rtn_tool_request.model_dump(exclude_none=True))
        return rtn_list

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
    def create_agent(cls, agent_config:Agent_Config)->Agent_Request_Result:
        result = Agent_Request_Result(
            agent_id='',
            request_type=Agent_Request_Type.CREATE,
            result_type=Agent_Request_Result_Type.SUCCESS,
        )

        allowd_local_tool_requests = []
        allowd_local_tool_funcs = []

        allowed_mcp_tool_requests = []
        allowed_mcp_tool_funcs = []

        # 最终包含local和MCP的所有allowed的funcs
        all_tool_funcs = []

        sub_agents_data_list = []

        try:
            # 获取所有的local tools
            if agent_config.allowed_local_tool_names:
                # --------------获取所有的普通local tools--------------
                for local_tool_request, local_tool_func in zip(cls.local_all_tool_requests, cls.local_all_tool_funcs):
                    if local_tool_request.name in agent_config.allowed_local_tool_names:
                        allowd_local_tool_requests.append(local_tool_request)
                        allowd_local_tool_funcs.append(local_tool_func)
                # -------------/获取所有的普通local tools--------------

                # -----------获取所有的local agent as tools-----------
                for agent_as_tool in cls.get_all_agents_as_tool():
                    if agent_as_tool.agent.agent_config.as_tool_name in agent_config.allowed_local_tool_names:
                        # 在upper agent中注册lower的agent_as_tool
                        sub_agents_data_list.append(agent_as_tool)

                        agent_as_tool_parameters = Tool_Parameters(
                            properties={'instruction': Tool_Property(type="string", description=config.Agent.SUB_AGENT_AS_TOOL_DESCRIPTION)},  # 这里参数必须是toolcall_agent.run(self, instruction)的instruction
                            required=['instruction'],
                        )

                        # 构造bound_func，解决deepcopy问题
                        # def _make_bound_func_of_agent_run(*args, **kwargs):
                        #     print(f'args={args}')
                        #     print(f'kwargs={kwargs}')
                        #     res = agent_as_tool.agent.run(query=kwargs['query'])
                        #     return res

                        agent_as_tool_request = Tool_Request(
                            name=agent_as_tool.agent.agent_config.as_tool_name,
                            description=agent_as_tool.agent.agent_config.as_tool_description,
                            parameters=agent_as_tool_parameters,
                            # func=agent_as_tool.agent.run,   # 注意这里是一个agent的成员函数run(self, query)，而python中，只要这里的func注册的是绑定对象如agent_obj.run()，后续回调就不需要输入self，如果是注册的是未绑定对象的如Toolcall_Agent.run，则回调需要输入self。（但是：obj或者obj.func存在pydantic中时，deepcopy都会报错）
                            # func=_make_bound_func_of_agent_run,   # 注意这里是一个agent的成员函数run(self, query)，而python中，只要这里的func注册的是绑定对象如agent_obj.run()，后续回调就不需要输入self，如果是注册的是未绑定对象的如Toolcall_Agent.run，则回调需要输入self。（但是：obj或者obj.func存在pydantic中时，deepcopy都会报错）
                            # func=Toolcall_Agent.run,   # 注意这里是一个agent的成员函数run(self, query)，而python中，只要这里的func注册的是绑定对象如agent_obj.run()，后续回调就不需要输入self，如果是注册的是未绑定对象的如Toolcall_Agent.run，则回调需要输入self。（但是：obj或者obj.func存在pydantic中时，deepcopy都会报错）
                        )
                        allowd_local_tool_requests.append(agent_as_tool_request)
                        allowd_local_tool_funcs.append(agent_as_tool.agent.run)
                # ----------/获取所有的local agent as tools-----------

            # 根据MCP url，添加allowed对应的tools
            if agent_config.mcp_requests:
                # --------------获取所有的MCP tools--------------
                for mcp_req in agent_config.mcp_requests:
                    if isinstance(mcp_req, MCP_Server_Request):
                        url = mcp_req.url
                        allowed_tool_names = mcp_req.allowed_tool_names
                    else:
                        url = mcp_req['url']
                        allowed_tool_names = mcp_req['allowed_tool_names']

                    dprint(f'mcp_url: {url!r}')
                    dprint(f'allowed_tool_names: {allowed_tool_names!r}')
                    try:
                        tool_requests, tool_funcs = get_mcp_server_tools(server_url=url, allowed_tools=allowed_tool_names)
                    except Exception as e:
                        info = f'MCP服务器解析失败（server_url: {url!r}, allowed_tool_names: {allowed_tool_names!r}）'
                        server_output(info)
                        continue

                    allowed_mcp_tool_requests += tool_requests
                    allowed_mcp_tool_funcs += tool_funcs
                # -------------、获取所有的MCP tools--------------

            # 整理所有tool的requests和funcs
            if agent_config.all_tool_requests is None:
                agent_config.all_tool_requests = []
            agent_config.all_tool_requests = allowd_local_tool_requests + allowed_mcp_tool_requests
            all_tool_funcs = allowd_local_tool_funcs + allowed_mcp_tool_funcs

        except Exception as e:
            err(e)
            result.result_type = Agent_Request_Result_Type.FAILED
            result.result_string = str(e)
            return result

        # agent初始化
        agent = Toolcall_Agent(agent_config=agent_config)
        agent.init(agent_config.all_tool_requests, all_tool_funcs)

        # 通过遍历，建立agent和sub_agent之间的关联（如cancel的遍历、level计算的遍历、设置top_agent_id的遍历）
        agent.calculate_all_agents_in_the_tree(sub_agents_data_list)

        # 注册agent
        agent_data = Agent_Data(
            agent_id=agent.agent_id,
            agent=agent,
        )
        cls.agents_dict[agent.agent_id] = agent_data

        result.agent_id = agent.agent_id

        # dprint()
        # dprint('--------------agent request result--------------')
        # dprint(result)
        # dprint('-------------/agent request result--------------')
        return result

    # 2、启动agent_id下的thread，并run
    @classmethod
    def run_agent(cls, agent_id:str, query)->Agent_Request_Result:
        result = Agent_Request_Result(
            agent_id=agent_id,
            request_type=Agent_Request_Type.RUN,
            result_type=Agent_Request_Result_Type.SUCCESS,
        )

        agent_data = cls.agents_dict[agent_id]
        agent = agent_data.agent

        if not agent:
            # agent不存在，退出
            result.result_type = Agent_Request_Result_Type.FAILED
            result.result_string = f'agent_id({agent_id!r})不存在.'
            return result

        if agent.agent_status.querying:
            # agent已经在quering了，run失败退出
            result.result_type = Agent_Request_Result_Type.FAILED
            result.result_string = f'agent(agent_id={agent_id!r})已在执行中，退出.'
            return result

        def _worker(query):
            agent.run(instruction=query)

        # 启动agent的thread
        agent_data.agent_thread = Thread(
            target=_worker,
            args=(query,),
        )
        agent_data.agent_thread.start()

        # dprint()
        # dprint('--------------agent request result--------------')
        # dprint(result)
        # dprint('-------------/agent request result--------------')
        return result

    # 3、等待agent的某次query(串行，暂不考虑并行和query_id)
    @classmethod
    def wait_agent(cls, agent_id)->Agent_Request_Result:
        result = Agent_Request_Result(
            agent_id=agent_id,
            request_type=Agent_Request_Type.WAIT,
            result_type=Agent_Request_Result_Type.SUCCESS,
        )

        thread = cls._get_thread(agent_id=agent_id)
        if thread:
            thread.join()
        else:
            result.result_type = Agent_Request_Result_Type.FAILED
            result.result_string = f'agent(agent_id={agent_id!r})未成功执行wait操作.'

        return result

    # 4、获取agent的实时状态
    @classmethod
    def get_agent_status(cls, agent_id)->Agent_Request_Result:
        result = Agent_Request_Result(
            agent_id=agent_id,
            request_type=Agent_Request_Type.GET_STATUS,
            result_type=Agent_Request_Result_Type.SUCCESS,
        )

        agent_data = cls.agents_dict[agent_id]
        if agent_data and agent_data.agent:
            result.result_content = agent_data.agent.agent_status
        else:
            result.result_type = Agent_Request_Result_Type.FAILED
            result.result_string = f'agent(agent_id={agent_id!r})未取得Agent_Status.'

        return result

    # 5、取消agent的run
    @classmethod
    def cancel_agent_run(cls, agent_id)->Agent_Request_Result:
        result = Agent_Request_Result(
            agent_id=agent_id,
            request_type=Agent_Request_Type.CANCEL,
            result_type=Agent_Request_Result_Type.SUCCESS,
        )

        agent_data = cls.agents_dict[agent_id]
        if agent_data and agent_data.agent:
            agent_data.agent.set_cancel()
        else:
            result.result_type=Agent_Request_Result_Type.FAILED
            result.result_string = f'agent(agent_id={agent_id!r})未成功执行cancel操作.'

        return result

    # 6、清除agent的历史
    @classmethod
    def clear_agent_history(cls, agent_id)->Agent_Request_Result:
        result = Agent_Request_Result(
            agent_id=agent_id,
            request_type=Agent_Request_Type.CLEAR_HISTORY,
            result_type=Agent_Request_Result_Type.SUCCESS,
        )

        agent_data = cls.agents_dict[agent_id]
        if agent_data and agent_data.agent:
            agent_data.agent.clear_history()
        else:
            result.result_type = Agent_Request_Result_Type.FAILED
            result.result_string = f'agent(agent_id={agent_id!r})未成功执行clear history操作.'

        return result

    # 根据agent_id，获取agent对象
    @classmethod
    def _get_agent(cls, agent_id:str)->Toolcall_Agent:
        agent_data = cls.agents_dict.get(agent_id)
        if agent_data and agent_data.agent:
            return agent_data.agent
        else:
            return None

    # 根据agent_id，获取thread
    @classmethod
    def _get_thread(cls, agent_id:str)->Thread:
        agent_data = cls.agents_dict.get(agent_id)
        if agent_data and agent_data.agent_thread:
            return agent_data.agent_thread
        else:
            return None

    # 获取MCP url对应的tools列表
    @classmethod
    def get_mcp_url_tool_names(cls, mcp_url:str)->List[str]:
        return get_mcp_server_tool_names(server_url=mcp_url)

    @classmethod
    async def get_mcp_url_tool_names_async(cls, mcp_url:str)->List[str]:
        return await get_mcp_server_tool_names_async(server_url=mcp_url)

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
    def parse_all_local_tools_on_server_start(cls):
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
        dprint(f'--------------server本地存放所有local tool的文件夹----------------')
        dprint(tools_dir)
        dprint(f'-------------/server本地存放所有local tool的文件夹----------------')

        tool_request_list = []
        tool_func_list = []
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

                            # if 'required' in obj.tool_parameters:
                            #     required_field_in_parameter = False
                            # else:
                            #     required_field_in_parameter = True

                            tool_request, tool_func = get_tool_request_and_func_from_tool_class(obj)
                            tool_request_list.append(tool_request)
                            tool_func_list.append(tool_func)

                except Exception as e:
                    dyellow(f"【Agent_Manager.server_init_local_tools_on_start】warning: 尝试动态导入 {filename} 失败: {e!r}")
                    continue

        return tool_request_list, tool_func_list

    # 供远程tool使用: 存储resource_data(会生成全局唯一的resource_id)
    @classmethod
    def save_resource(cls, resource_data:Resource_Data)->str:
        resource_id = Redis_Resource_Manager.set_resource(resource_data)
        return resource_id

    # 供远程tool使用: 读取resource_data, 用于client的远程tool调用
    @classmethod
    def load_resource(cls, resource_id:str)->Resource_Data:
        resource_data = Redis_Resource_Manager.get_resource(resource_id)
        return resource_data

    # 遍历整个agents的tree(仅用于server本地调用，因为远程无法设置on_node())
    @classmethod
    def _traverse_agents_tree(cls, agent_id:str, on_node:Callable[[Toolcall_Agent, str], Any], parent_agent_id=''):
        agent = cls._get_agent(agent_id)

        on_node(agent, parent_agent_id)

        if agent:
            for sub_agent in agent.sub_agents:
                cls._traverse_agents_tree(agent_id=sub_agent.agent_id, on_node=on_node, parent_agent_id=agent.agent_id)

def main_one_agent():
    from web_socket_server import Web_Socket_Server_Manager
    # from agent.tools.folder_tool import Folder_Tool
    # fold_tool = Folder_Tool.get_tool_param_dict()

    # tool_list = Agent_Manager.parse_all_local_tools_on_server_start()
    local_tool_requests, local_tool_funcs = Agent_Manager.init()
    dprint("--------------tools_info------------------")
    for tool_param_dict in local_tool_requests:
        dprint(tool_param_dict)
    dprint("-------------/tools_info------------------")

    dprint("--------------client_get_server_local_tools_info------------------")
    dprint(Agent_Manager.get_local_tool_names())
    dprint(Agent_Manager.get_local_tool_param_dict(tool_name='Write_Chapter_Tool'))
    dprint(Agent_Manager.get_local_tool_param_dict(tool_name='Folder_Tool'))
    dprint(Agent_Manager.get_local_tool_param_dict(tool_name='Insert_Math_Formula_Tool'))
    dprint("--------------client_get_server_local_tools_info------------------")



    dprint("--------------MCP------------------")
    dpprint(Agent_Manager.get_mcp_url_tool_names("https://powerai.cc:8011/mcp/sqlite/sse"))
    # dpprint(Agent_Manager.get_mcp_url_tool_names("http://localhost:8789/sse"))
    dprint("-------------/MCP------------------")

    mcp_requests = [
        MCP_Server_Request(url="https://powerai.cc:8011/mcp/sqlite/sse", allowed_tool_names=['list_tables', 'read_query']),
        # MCP_Server_Request(url="http://localhost:8789/sse", allowed_tool_names=['tavily-search']),
    ]

    agent_config = Agent_Config(
        llm_config=llm_protocol.g_local_gpt_oss_120b_mxfp4_lmstudio,
        agent_name='Agent created by Agent_Manager',
        allowed_local_tool_names=['Insert_Math_Formula_Tool'],
        # allowed_local_tool_names=['Folder_Tool'],
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

    res = Agent_Manager.run_agent(agent_id=agent_id, query='帮我插入一个定积分公式。')
    # res = Agent_Manager.run_agent(agent_id=agent_id, query='帮我在文档中插入一个复杂的数学公式')
    # res = Agent_Manager.run_agent(agent_id=agent_id, query='请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，需要遍历每一个子文件夹，一定能找到')
    dprint("--------------run_agent------------------")
    dprint(f'result=({res})')
    dprint("-------------/run_agent------------------")



    # dprint("-----------------------------------------------------------")
    # while True:
    #     res = Agent_Manager.run_agent(agent_id=agent_id, query='你刚才搜索file_to_find.txt这个文件的位置的结果是啥来着')
    #     if res.result_type==Agent_Request_Result_Type.SUCCESS:
    #         break
    #     time.sleep(0.1)
    # dprint("-----------------------------------------------------------")


    # Agent_Manager.run_agent(agent_id=agent_id, query='请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，递归搜索所有子文件夹直到准确找到该文件')
    # Agent_Manager.run_agent(agent_id=agent_id, query='有哪些表格？')
    # Agent_Manager.run_agent(agent_id=agent_id, query='通信录表里有哪些数据？')

    Agent_Manager.wait_agent(agent_id=agent_id)

    from web_socket_server import Web_Socket_Server_Manager
    Web_Socket_Server_Manager.stop_all_servers()

def main_multi_levels_agents():
    # from agent.tools.folder_tool import Folder_Tool
    # fold_tool = Folder_Tool.get_tool_param_dict()

    # tool_list = Agent_Manager.parse_all_local_tools_on_server_start()
    local_tool_quests, local_tool_funcs = Agent_Manager.init()
    # print(f'local_tool_quests={Agent_Manager.get_local_all_tool_info_json()}')
    dprint("--------------所有local tools的信息------------------")
    for tool_param_dict in local_tool_quests:
        dprint(tool_param_dict)
    dprint("-------------/所有local tools的信息------------------")

    dprint("--------------指定tool_name的local tool的信息------------------")
    dprint(Agent_Manager.get_local_tool_names())
    dprint(Agent_Manager.get_local_tool_param_dict(tool_name='Write_Chapter_Tool'))
    dprint(Agent_Manager.get_local_tool_param_dict(tool_name='Folder_Tool'))
    dprint("-------------/指定tool_name的local tool的信息------------------")

    dprint("--------------指定url的MCP的所有tool_name------------------")
    url = "https://powerai.cc:8011/mcp/sqlite/sse"
    dprint(f'url={url}')
    dpprint(Agent_Manager.get_mcp_url_tool_names(url))
    # dpprint(Agent_Manager.get_mcp_url_tool_names("http://localhost:8789/sse"))

    # npx @playwright/mcp@latest --port 8788 --headless --browser chromium
    url = "http://localhost:8788/sse"
    dprint(f'url={url}')
    dpprint(Agent_Manager.get_mcp_url_tool_names(url))
    dprint("-------------/指定url的MCP的所有tool_name------------------")

    mcp_requests = [
        MCP_Server_Request(url="https://powerai.cc:8011/mcp/sqlite/sse", allowed_tool_names=['list_tables', 'read_query']),
        MCP_Server_Request(url="http://localhost:8789/sse", allowed_tool_names=['tavily-search']),
        MCP_Server_Request(url="http://localhost:8788/sse"),
    ]
    mcp_playwright_requests = [
        MCP_Server_Request(url="http://localhost:8788/sse"),
    ]

    # llm_c = llm_protocol.g_online_qwen3_next_80b_thinking
    llm_c = llm_protocol.g_online_qwen3_next_80b_instruct
    # llm_c = llm_protocol.g_local_gpt_oss_120b_mxfp4_lmstudio

    # -----------------------------注册2层agent as tool-----------------------------------
    agent_config = Agent_Config(
        # llm_config=llm_protocol.g_online_deepseek_chat,
        llm_config=llm_c,
        agent_name='agent level 1-playwright',
        # allowed_local_tool_names=['browser_navigate', 'browser_wait_for', 'browser_network_requests', ''],
        mcp_requests=mcp_playwright_requests,
        as_tool_name='Playwright_Tool',
        as_tool_description='本工具用来调用playwright的工具',
    )
    res = Agent_Manager.create_agent(agent_config)

    agent_config = Agent_Config(
        # llm_config=llm_protocol.g_online_deepseek_chat,
        llm_config=llm_c,
        agent_name='agent level 2-Folder_Tool_Level_2',
        allowed_local_tool_names=['Folder_Tool'],
        as_tool_name='Folder_Tool_Level_2',
        as_tool_description='本工具用来在文件夹中搜索指定文件',
    )
    res = Agent_Manager.create_agent(agent_config)

    agent_config = Agent_Config(
        # llm_config=llm_protocol.g_online_deepseek_chat,
        llm_config=llm_c,
        agent_name='agent level 1-Folder_Tool_Level_1',
        allowed_local_tool_names=['Folder_Tool_Level_2'],
        as_tool_name='Folder_Tool_Level_1',
        as_tool_description='本工具用来在文件夹中搜索指定文件',
    )
    res = Agent_Manager.create_agent(agent_config)
    # ----------------------------/注册一2层agent as tool-----------------------------------

    agent_config = Agent_Config(
        # llm_config=llm_protocol.g_online_deepseek_chat,
        llm_config=llm_c,
        # llm_config=llm_protocol.g_online_groq_gpt_oss_120b,
        agent_name='agent level 0-top agent',
        allowed_local_tool_names=['Folder_Tool_Level_1', 'Playwright_Tool'],
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
    # dprint()
    # dprint('--------------agent request result--------------')
    # dprint(res)
    # dprint('-------------/agent request result--------------')
    agent_id = res.agent_id

    dprint("--------------注册后tool情况------------------")
    for info in Agent_Manager._get_all_tool_debug_info_list(agent_id):
        dprint(info)
    dprint("-------------/注册后tool情况------------------")

    def _on_node(agent, parent_agent_id):
        level = agent.agent_level
        top_agent_id = agent.top_agent_id
        print(f'{"   "*level} agent_id={agent.agent_id!r}, parent_agent_id={parent_agent_id!r}, top_agent_id={top_agent_id}, agent_name={agent.agent_config.agent_name}')

    dprint("---------------------------------------完整agents tree--------------------------------------------")
    Agent_Manager._traverse_agents_tree(agent_id=agent_id, on_node=_on_node)
    dprint("--------------------------------------/完整agents tree--------------------------------------------")

    # res = Agent_Manager.run_agent(agent_id=agent_id, query='现代物理学的创始人是谁')
    # res = Agent_Manager.run_agent(agent_id=agent_id, query='https://www.ccps.gov.cn/xtt/202410/t20241004_164720.shtml这个链接的网页内容讲了什么？')
    res = Agent_Manager.run_agent(agent_id=agent_id, query='请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，需要遍历每一个子文件夹，一定能找到')
    # Agent_Manager.wait_agent(agent_id=agent_id)

    # debug_cancel = True
    debug_cancel = False

    if debug_cancel:
        time.sleep(3)
        Agent_Manager.cancel_agent_run(agent_id=agent_id)

    while True:
        # res = Agent_Manager.run_agent(agent_id=agent_id, query='你刚才分析的网页内容是什么？')
        res = Agent_Manager.run_agent(agent_id=agent_id, query='你刚才搜索file_to_find.txt这个文件的位置的结果是啥来着')
        if res.result_type==Agent_Request_Result_Type.SUCCESS:
            # Agent_Manager.clear_agent_history(agent_id=agent_id)
            if debug_cancel:
                time.sleep(5)
                Agent_Manager.cancel_agent_run(agent_id=res.agent_id)
            break

        time.sleep(0.1)

    # Agent_Manager.wait_agent(agent_id=agent_id)


    # Agent_Manager.run_agent(agent_id=agent_id, query='请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，递归搜索所有子文件夹直到准确找到该文件')
    # Agent_Manager.run_agent(agent_id=agent_id, query='有哪些表格？')
    # Agent_Manager.run_agent(agent_id=agent_id, query='通信录表里有哪些数据？')

    Agent_Manager.wait_agent(agent_id=agent_id)

    from web_socket_server import Web_Socket_Server_Manager
    Web_Socket_Server_Manager.stop_all_servers()

if __name__ == "__main__":
    main_one_agent()
    # main_multi_levels_agents()