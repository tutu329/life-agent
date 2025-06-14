from typing import List, Dict, Any
from pydantic import BaseModel, ConfigDict
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import Future
import time

from agent.core.tool_agent import Tool_Agent
from agent.core.agent_config import Agent_Config, Agent_As_Tool_Config
from agent.tools.tool_manager import legacy_get_all_local_tools_class, get_all_registered_tools_class, server_register_tool, server_get_tool_data_by_id
from agent.core.protocol import Agent_Status, Agent_Stream_Queues

from config import dblue, dyellow, dred, dgreen, dcyan

class Registered_Agent_Data(BaseModel):
    agent_id            :str
    agent_obj           :Tool_Agent
    agent_future        :Future
    # agent_status        :Agent_Status
    agent_stream_queues :Agent_Stream_Queues

    # 开启“任意类型”支持
    model_config = ConfigDict(arbitrary_types_allowed=True)

# 全局存储agent实例的注册( agent_id <--> Tool_Agent实例 )
g_registered_agents_dict: Dict[str, Registered_Agent_Data] = {}

# 全局线程池，真正业务里可以按需设置 max_workers
g_thread_pool_executor = ThreadPoolExecutor()

# server启动一个agent的query，并注册
def server_start_and_register_agent(
    query:str,
    agent_config:Agent_Config,
    tool_names:List[str],
    exp_json_path:str,
)->str:     # 返回agent_id
    # agent_id = str(uuid4())

    # multi_agent_server和tool_agent同步管理的信息
    agent_status = Agent_Status()
    # agent_stream_queue = Agent_Stream_Queues()

    # 初始化tool_agent
    class_list = get_all_registered_tools_class(tool_names)
    print(f'class_list: {class_list!r}')
    # class_list = get_all_local_tools_class(tool_names)
    agent = Tool_Agent(
        has_history=True,
        tool_classes=class_list,
        agent_config=agent_config,
        # agent_status_ref=agent_status,
        # agent_stream_queue_ref=agent_stream_queue,
        tool_agent_experience_json_path=exp_json_path,
    )
    agent_id = agent.agent_id

    def _run_agent_thread():
        agent.init()
        success = agent.run(query=query)

    # thread = Thread(target=_run_agent_thread)
    # thread.start()

    # 如果用with ThreadPoolExecutor() as pool:，则ThreadPoolExecutor 作为一个上下文管理器（with 语句）时，会在离开 with 块时自动调用 executor.shutdown(wait=True)。
    # 而shutdown(wait=True) 会 阻塞直到所有提交的任务执行完毕，因此退出上下文时，thread已经完成，即获得的future实际上已经变成了done()
    future = g_thread_pool_executor.submit(_run_agent_thread)

    # 初始化agent的注册数据
    agent_data = Registered_Agent_Data(
        agent_id=agent_id,
        agent_obj=agent,
        agent_future=future,
        # agent_status=agent_status,
        agent_stream_queues=agent.stream_queues
    )

    # 注册agent的数据
    g_registered_agents_dict[agent_id] = agent_data

    return agent_id

# agent后续轮的query
def server_continue_agent(agent_id, query):
    agent_data = g_registered_agents_dict[agent_id]
    agent = agent_data.agent_obj

    def _run_agent_thread():
        agent.unset_cancel()
        # dred(f'-----------------------history1----------------------------')
        # print(agent.agent_tools_description_and_full_history)
        # dred(f'----------------------/history1----------------------------')
        success = agent.run(query=query)
        # dred(f'-----------------------history2----------------------------')
        # print(agent.agent_tools_description_and_full_history)
        # dred(f'----------------------/history2----------------------------')
    future = g_thread_pool_executor.submit(_run_agent_thread)

    # 更新线程的future
    agent_data.agent_future = future

    return agent_data

# 返回agent的状态
def server_get_agent_status(agent_id)->Agent_Status:
    if g_registered_agents_dict.get(agent_id):
        agent_status = g_registered_agents_dict[agent_id].agent_obj.status
        return agent_status

def print_agent_status(agent_id):
    if g_registered_agents_dict.get(agent_id):
        agent_status = g_registered_agents_dict[agent_id].agent_obj.status
        # agent_stream_queue = g_registered_agents_dict[agent_id].agent_stream_queues

        dblue(f'-------------------------agent status(agent_id="{agent_id}")-------------------------------')
        dyellow(f'{"agent status:":<30}({agent_status})')
        # dyellow(f'{"agent stream output:":<30}({agent_stream_queue.output})')
        # dyellow(f'{"agent stream thinking:":<30}({agent_stream_queue.thinking})')
        # dyellow(f'{"agent stream log:":<30}({agent_stream_queue.log})')
        # dyellow(f'{"agent stream tool_rtn_data:":<30}({agent_stream_queue.tool_rtn_data})')
        dblue(f'------------------------/agent status(agent_id="{agent_id}")-------------------------------')

# 对agent进行cancel操作
def server_cancel_agent(agent_id):
    agent_data = g_registered_agents_dict[agent_id]
    agent_data.agent_obj.set_cancel()
    dyellow(f'agent正在cancel中...(agent_id: "{agent_id}")')

# # 对agent进行pause操作
# def server_pause_agent(agent_id):
#     agent_data = g_registered_agents_dict[agent_id]
#     agent_data.agent_obj.set_pause()
#     dyellow(f'agent已经paused...(agent_id: "{agent_id}")')
#
# # 对agent进行un-pause操作
# def server_unpause_agent(agent_id):
#     agent_data = g_registered_agents_dict[agent_id]
#     agent_data.agent_obj.unset_pause()
#     dyellow(f'agent已经取消paused...(agent_id: "{agent_id}")')

# server等待一个agent的future到done
def __server_wait_registered_agent(agent_id, timeout_second=10):
    agent_data = g_registered_agents_dict[agent_id]
    future = agent_data.agent_future

    # try:
    #     future.result(timeout=5)
    # except TimeoutError:
    #     print("任务超时，Future 继续跑，但我不等了")

    # future.result(timeout=5)
    i=0
    dred(f'__server_wait_registered_agent() invoked.')
    while not future.done():
        # print("还没好，再等⏳")
        time.sleep(1)
        i += 1
        # if i>10:
        # dred(f'【第{i}秒】')
        if i>timeout_second:
            dred(f'server_cancel_agent() invoked.')
            server_cancel_agent(agent_id)
            # break

    dblue(f'agent任务执行完毕(agent_id="{agent_id}").')

    # 此时可以考虑删除agent_id对应的注册数据
    # del g_registered_agents_dict[agent_id]
    # dblue(f'agent实例已经删除(agent_id="{agent_id}").')

# server返回一个agent的数据
def server_get_registered_agent_data(agent_id):
    return g_registered_agents_dict[agent_id]

# 多层agent体系的关键(前后端系统)
# server创建agent_as_tool
# def _server_create_and_registered_agent_as_tool(
#     tool_names:List[str],       # 该agent所需调用tools的name list
#     agent_config:Agent_Config,        # agent的config
#     as_tool_name:str,           # name as tool
#     as_tool_description:str,    # description as tool
# ):
#     # 获取该agent需要使用的tools_class_list
#     tools_class_list = get_all_registered_tools_class(tool_names)
#     # tools_class_list = legacy_get_all_local_tools_class(tool_names)
#
#     # 生成agent(继承自Base_Tool)的实例
#     agent_as_tool = Tool_Agent(
#         tool_classes=tools_class_list,
#         agent_config=agent_config,
#         as_tool_name=as_tool_name,
#         as_tool_description=as_tool_description,
#         tool_agent_experience_json_path='',     #agent_as_tool不需要经验，经验由upper agent管理
#     ).init()
#
#     # 注册agent_as_tool
#     tool_id = server_register_tool(
#         name=as_tool_name,
#         description=as_tool_description,
#         parameters=[],                          # 这里不需要具体信息，Tool_Agent会自动注入agent_as_tool的固定的'自然语言指令'para
#         tool_class_or_instance=agent_as_tool,   # 这里因为是agent_as_tool，所以将instance而非class传入
#     )
#
#     return tool_id

def _server_create_and_registered_agent_as_tool(
    # tool_names:List[str],       # 该agent所需调用tools的name list
    # agent_config:Agent_Config,  # agent的config
    # as_tool_name:str,           # name as tool
    # as_tool_description:str,    # description as tool

    agent_as_tool_config:Agent_As_Tool_Config
):
    # 获取该agent需要使用的tools_class_list
    tools_class_list = get_all_registered_tools_class(agent_as_tool_config.tool_names)
    # tools_class_list = legacy_get_all_local_tools_class(tool_names)

    agent_config = Agent_Config(
        tool_names=agent_as_tool_config.tool_names,
        exp_json_path=agent_as_tool_config.exp_json_path,
        base_url=agent_as_tool_config.base_url,
        api_key=agent_as_tool_config.api_key,
        llm_model_id=agent_as_tool_config.llm_model_id,
        temperature=agent_as_tool_config.temperature
    )

    # 生成agent(继承自Base_Tool)的实例
    agent_as_tool = Tool_Agent(
        tool_classes=tools_class_list,
        agent_config=agent_config,
        as_tool_name=agent_as_tool_config.as_tool_name,
        as_tool_description=agent_as_tool_config.as_tool_description,
        tool_agent_experience_json_path='',     #agent_as_tool不需要经验，经验由upper agent管理
    ).init()

    # 注册agent_as_tool
    tool_id = server_register_tool(
        name=agent_as_tool_config.as_tool_description,
        description=agent_as_tool_config.as_tool_description,
        parameters=[],                          # 这里不需要具体信息，Tool_Agent会自动注入agent_as_tool的固定的'自然语言指令'para
        tool_class_or_instance=agent_as_tool,   # 这里因为是agent_as_tool，所以将instance而非class传入
    )

    return tool_id

# def server_start_and_register_2_levels_agents_system(
#     query                   :str,
#     upper_agent_config      :Agent_Config,                  # 顶层agent的配置
#     lower_agents_config     :List[Agent_As_Tool_Config],    # 下层agent的配置（多个）
# )->Registered_Agent_Data:
#     # ----------------构建lower的agents_as_tool----------------
#     # 所有将创建的agent_as_tool对应的tool_id_list
#     agents_as_tool_id_list = []
#
#     # 创建所有agent_as_tool
#     for lower_agent_config in lower_agents_config:
#         tool_id = _server_create_and_registered_agent_as_tool(lower_agent_config)
#         agents_as_tool_id_list.append(tool_id)
#     # ---------------/构建lower的agents_as_tool----------------
#
#     # ----------------构建upper的agent----------------
#     # multi_agent_server和tool_agent同步管理的信息
#     upper_agent_status = Agent_Status()
#     # upper_agent_stream_queue = Agent_Stream_Queues()
#
#     # upper_agent需要将所有agent_as_tool和常规tools的融合
#     agents_as_tool_instance_list = []
#     for agents_as_tool_id in agents_as_tool_id_list:
#         instance = server_get_tool_data_by_id(agents_as_tool_id).tool_class
#         agents_as_tool_instance_list.append(instance)
#
#     upper_agent_tools_class_list = get_all_registered_tools_class(upper_agent_config.tool_names)
#     # upper_agent_tools_class_list = legacy_get_all_local_tools_class(upper_agent_dict['tool_names'])
#     tool_class_and_tool_instance_list = upper_agent_tools_class_list + agents_as_tool_instance_list
#
#     # dred('---------------------upper_agent_tools_class_list-------------------------')
#     # print(upper_agent_tools_class_list)
#     # dred('--------------------/upper_agent_tools_class_list-------------------------')
#     #
#     # dred('---------------------agents_as_tool_instance_list-------------------------')
#     # print(agents_as_tool_instance_list)
#     # dred('--------------------/agents_as_tool_instance_list-------------------------')
#     #
#     #
#     # dred('---------------------tool_class_and_tool_instance_list--------------------')
#     # print(tool_class_and_tool_instance_list)
#     # dred('--------------------/tool_class_and_tool_instance_list--------------------')
#
#     # ---------------/构建upper的agent----------------
#     upper_agent = Tool_Agent(
#         has_history=True,
#         tool_classes=tool_class_and_tool_instance_list,     # 这里是[Tool_Class1, Tool_Class2, ... , agent_as_tool1, agent_as_tool2, ...]
#         agent_config=upper_agent_config,
#         # agent_status_ref=upper_agent_status,
#         # agent_stream_queue_ref=upper_agent_stream_queue,
#         tool_agent_experience_json_path = upper_agent_config.exp_json_path,
#     )
#     upper_agent_id = upper_agent.agent_id
#
#     def _run_agent_thread():
#         upper_agent.init()
#         success = upper_agent.run(query=query)
#
#     future = g_thread_pool_executor.submit(_run_agent_thread)
#
#     # 初始化agent的注册数据
#     agent_data = Registered_Agent_Data(
#         agent_id=upper_agent_id,
#         agent_obj=upper_agent,
#         agent_future=future,
#         # agent_status=upper_agent_status,
#         agent_stream_queues=upper_agent.stream_queues
#     )
#
#     # 注册agent的数据
#     g_registered_agents_dict[upper_agent_id] = agent_data
#
#     return agent_data
#     # return upper_agent_id

def server_start_and_register_2_levels_agents_system(
    upper_agent_config      :Agent_Config,                  # 顶层agent的配置
    lower_agents_config     :List[Agent_As_Tool_Config],    # 下层agent的配置（多个）
)->Registered_Agent_Data:
    # ----------------构建lower的agents_as_tool----------------
    # 所有将创建的agent_as_tool对应的tool_id_list
    agents_as_tool_id_list = []

    # 创建所有agent_as_tool
    for lower_agent_config in lower_agents_config:
        tool_id = _server_create_and_registered_agent_as_tool(lower_agent_config)
        agents_as_tool_id_list.append(tool_id)
    # ---------------/构建lower的agents_as_tool----------------

    # ----------------构建upper的agent----------------
    # multi_agent_server和tool_agent同步管理的信息
    upper_agent_status = Agent_Status()
    # upper_agent_stream_queue = Agent_Stream_Queues()

    # upper_agent需要将所有agent_as_tool和常规tools的融合
    agents_as_tool_instance_list = []
    for agents_as_tool_id in agents_as_tool_id_list:
        instance = server_get_tool_data_by_id(agents_as_tool_id).tool_class
        agents_as_tool_instance_list.append(instance)

    upper_agent_tools_class_list = get_all_registered_tools_class(upper_agent_config.tool_names)
    # upper_agent_tools_class_list = legacy_get_all_local_tools_class(upper_agent_dict['tool_names'])
    tool_class_and_tool_instance_list = upper_agent_tools_class_list + agents_as_tool_instance_list

    # dred('---------------------upper_agent_tools_class_list-------------------------')
    # print(upper_agent_tools_class_list)
    # dred('--------------------/upper_agent_tools_class_list-------------------------')
    #
    # dred('---------------------agents_as_tool_instance_list-------------------------')
    # print(agents_as_tool_instance_list)
    # dred('--------------------/agents_as_tool_instance_list-------------------------')
    #
    #
    # dred('---------------------tool_class_and_tool_instance_list--------------------')
    # print(tool_class_and_tool_instance_list)
    # dred('--------------------/tool_class_and_tool_instance_list--------------------')

    # ---------------/构建upper的agent----------------
    upper_agent = Tool_Agent(
        has_history=True,
        tool_classes=tool_class_and_tool_instance_list,     # 这里是[Tool_Class1, Tool_Class2, ... , agent_as_tool1, agent_as_tool2, ...]
        agent_config=upper_agent_config,
        # agent_status_ref=upper_agent_status,
        # agent_stream_queue_ref=upper_agent_stream_queue,
        tool_agent_experience_json_path = upper_agent_config.exp_json_path,
    )
    upper_agent_id = upper_agent.agent_id

    # ---------------------注入top_agent_id------------------------
    # 因为lower_agent先初始化，所以只能在upper_agent初始化之后，遍历所有lower_agent注入top_agent_id
    for agent_as_tool_instance in agents_as_tool_instance_list:
        # print(f'agent_as_tool_instance: ({agent_as_tool_instance})')
        agent_as_tool_instance.set_top_agent_id(upper_agent=upper_agent)
    # --------------------/注入top_agent_id------------------------

    # def _run_agent_thread():
    #     upper_agent.init()

    upper_agent.init()

    # 初始化agent的注册数据
    agent_data = Registered_Agent_Data(
        agent_id=upper_agent_id,
        agent_obj=upper_agent,
        agent_future=Future(),  # 这里其实不需要future，但是pydantic要验证
        # agent_status=upper_agent_status,
        agent_stream_queues=upper_agent.stream_queues
    )

    # 注册agent的数据
    g_registered_agents_dict[upper_agent_id] = agent_data

    return agent_data
    # return upper_agent_id

# # 2层agent系统的后续轮的query
# def server_continue_2_levels_agents_system(agent_id, query):
#     upper_agent_data = g_registered_agents_dict[agent_id]
#     upper_agent = upper_agent_data.agent_obj
#
#     def _run_agent_thread():
#         upper_agent.unset_cancel()
#         success = upper_agent.run(query=query)
#     future = g_thread_pool_executor.submit(_run_agent_thread)
#
#     # 更新线程的future
#     upper_agent_data.agent_future = future

# 测试remote_tool调用（Remote_Folder_Tool）
def main_test_server_start_agent():
    from agent.tools.tool_manager import print_all_registered_tools, server_register_all_local_tool_on_start, server_register_remote_tool_dynamically, Registered_Remote_Tool_Data
    # main_test_register_remote_tool_dynamically()

    # --------注册一个远程tool(需要远程开启该tool call的fastapi)--------
    # 注册local所有tool
    server_register_all_local_tool_on_start()
    reg_data = Registered_Remote_Tool_Data(
        name="Remote_Folder_Tool",
        description="返回远程服务器上指定文件夹下所有文件和文件夹的名字信息。",
        parameters=[
            {
                "name": "file_path",
                "type": "string",
                "description": "本参数为文件夹所在的路径",
                "required": "True",
            }
        ],
        endpoint_url="http://localhost:5120/remote_folder_tool",
        method="POST",
        timeout=15,
    )
    tool_id = server_register_remote_tool_dynamically(reg_data)
    print_all_registered_tools()
    # -------/注册一个远程tool(需要远程开启该tool call的fastapi)--------

    tool_names = ['Human_Console_Tool', 'Remote_Folder_Tool']
    # tool_names = ['Human_Console_Tool', 'Folder_Tool']
    config = Agent_Config(
        base_url='https://api.deepseek.com/v1',
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        llm_model_id='deepseek-chat'
    )
    # query='我叫土土，帮我查询下远程服务器下/home/tutu/models/下有哪些文件'
    query='我叫土土，当前目录./下有哪些文件'

    agent_id = server_start_and_register_agent(
        query=query,
        exp_json_path='agent_started_by_server.json',
        agent_config=config,
        tool_names=tool_names
    )

    time.sleep(0.5)
    print_agent_status(agent_id)
    # __server_wait_registered_agent(agent_id, timeout_second=30)
    __server_wait_registered_agent(agent_id, timeout_second=20000000)

    # server_continue_agent(agent_id, query='我刚才告诉你我叫什么？')
    #
    # print_agent_status(agent_id)

# 测试2层agent系统（含remote_tool调用：Remote_Folder_Tool）
def main_test_2_level2_agents_system():
    from agent.tools.tool_manager import print_all_registered_tools, server_register_all_local_tool_on_start, server_register_remote_tool_dynamically, Registered_Remote_Tool_Data
    # query: str,
    # upper_agent_dict: Dict[str, Any],
    # # {'tool_names':tool_names, 'exp_json_path':exp_json_path, 'agent_config':agent_config}
    # lower_agents_as_tool_dict_list: List[Dict[str, Any]],
    # # [{'tool_names':tool_names, 'agent_config':agent_config, 'as_tool_name':as_tool_name, 'as_tool_description':as_tool_description}, ...]

    # --------注册一个远程tool(需要远程开启该tool call的fastapi)--------
    # 注册local所有tool
    server_register_all_local_tool_on_start()
    reg_data = Registered_Remote_Tool_Data(
        name="Remote_Folder_Tool",
        description="返回远程服务器上指定文件夹下所有文件和文件夹的名字信息。",
        parameters=[
            {
                "name": "file_path",
                "type": "string",
                "description": "本参数为文件夹所在的路径",
                "required": "True",
            }
        ],
        endpoint_url="http://localhost:5120/remote_folder_tool",
        method="POST",
        timeout=15,
    )
    tool_id = server_register_remote_tool_dynamically(reg_data)
    print_all_registered_tools()
    # -------/注册一个远程tool(需要远程开启该tool call的fastapi)--------

    query = r'我叫土土，请告诉我当前文件夹下有哪些文件'
    config = Agent_Config(
        base_url='https://api.deepseek.com/v1',
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        llm_model_id='deepseek-chat',     # 模型指向 DeepSeek-V3-0324
    )
    upper_agent_dict = {
        'tool_names':['Human_Console_Tool'],
        'exp_json_path':'my_2_levels_mas_exp.json',
        'agent_config':config,
    }
    lower_agents_as_tool_dict_list = [
        {
            'tool_names':['Human_Console_Tool', 'Remote_Folder_Tool'],
            # 'tool_names':['Human_Console_Tool', 'Folder_Tool'],
            'agent_config':config,
            'as_tool_name':'Folder_Agent_As_Tool',
            'as_tool_description':'本工具用于获取文件夹中的文件和文件夹信息'
        }
    ]
    agent_id = server_start_and_register_2_levels_agents_system(
        query=query,
        upper_agent_dict=upper_agent_dict,
        lower_agents_as_tool_dict_list=lower_agents_as_tool_dict_list
    )

    time.sleep(0.5)
    print_agent_status(agent_id)
    # __server_wait_registered_agent(agent_id, timeout_second=30)
    __server_wait_registered_agent(agent_id, timeout_second=20000000)

    # server_continue_agent(agent_id, query='我刚才告诉你我叫什么？')

    # print_agent_status(agent_id)

if __name__ == "__main__":
    # main_test_server_start_agent()
    main_test_2_level2_agents_system()
