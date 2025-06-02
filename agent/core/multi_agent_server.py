from typing import List, Dict, Any, Type
from pydantic import BaseModel, Field, ConfigDict
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from concurrent.futures import Future
import time

from agent.core.tool_agent import Tool_Agent
from agent.core.agent_config import Config
from agent.core.tool_manager import get_tools_class
from agent.core.protocol import Agent_Status, Agent_Stream_Queue

from config import dred,dgreen,dblue,dcyan,dyellow

class Registered_Agent_Data(BaseModel):
    agent_id            :str
    agent_obj           :Tool_Agent
    agent_future        :Future
    agent_status        :Agent_Status
    agent_stream_queue  :Agent_Stream_Queue

    # 开启“任意类型”支持
    model_config = ConfigDict(arbitrary_types_allowed=True)

# 全局存储agent实例的注册( agent_id <--> Tool_Agent实例 )
g_registered_agents_dict: Dict[str, Registered_Agent_Data] = {}

# 全局线程池，真正业务里可以按需设置 max_workers
g_thread_pool_executor = ThreadPoolExecutor()

# server启动一个agent，返回对应的唯一agent_id
def server_start_and_register_agent(
    query:str,
    agent_config:Config,
    tool_names:List[str]
)->str:     # 返回agent_id
    # agent_id = str(uuid4())

    # multi_agent_server和tool_agent同步管理的信息
    agent_status = Agent_Status()
    agent_stream_queue = Agent_Stream_Queue()

    # 初始化tool_agent
    class_list = get_tools_class(tool_names)
    agent = Tool_Agent(
        has_history=True,
        tool_classes=class_list,
        agent_config=agent_config,
        agent_status_ref=agent_status,
        agent_stream_queue_ref=agent_stream_queue
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
        agent_status=agent_status,
        agent_stream_queue=agent_stream_queue
    )

    # 注册agent的数据
    g_registered_agents_dict[agent_id] = agent_data

    return agent_id

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

def print_agent_status(agent_id):
    if g_registered_agents_dict.get(agent_id):
        agent_status = g_registered_agents_dict[agent_id].agent_status
        agent_stream_queue = g_registered_agents_dict[agent_id].agent_stream_queue

        dblue(f'-------------------------agent started(agent_id="{agent_id}")-------------------------------')
        dyellow(f'{"agent status:":<30}({agent_status})')
        dyellow(f'{"agent stream output:":<30}({agent_stream_queue.output})')
        dyellow(f'{"agent stream thinking:":<30}({agent_stream_queue.thinking})')
        dyellow(f'{"agent stream log:":<30}({agent_stream_queue.log})')
        dyellow(f'{"agent stream tool_rtn_data:":<30}({agent_stream_queue.tool_rtn_data})')
        dblue(f'------------------------/agent started(agent_id="{agent_id}")-------------------------------')

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
def server_wait_registered_agent(agent_id):
    agent_data = g_registered_agents_dict[agent_id]
    future = agent_data.agent_future

    # try:
    #     future.result(timeout=5)
    # except TimeoutError:
    #     print("任务超时，Future 继续跑，但我不等了")

    # future.result(timeout=5)
    i=0
    while not future.done():
        # print("还没好，再等⏳")
        time.sleep(0.5)
        i += 1
        if i>10:
            server_cancel_agent(agent_id)
            # break

    dblue(f'agent任务执行完毕(agent_id="{agent_id}").')

    # 此时可以考虑删除agent_id对应的注册数据
    # del g_registered_agents_dict[agent_id]
    # dblue(f'agent实例已经删除(agent_id="{agent_id}").')

# server返回一个agent的数据
def server_get_registered_agent_data(agent_id):
    return g_registered_agents_dict[agent_id]

def main_test_server_start_agent():
    tool_names = ['Human_Console_Tool', 'Folder_Tool']
    config = Config(
        base_url='https://api.deepseek.com/v1',
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        model_id='deepseek-chat'
    )
    query='我叫土土，当前目录下有哪些文件'

    agent_id = server_start_and_register_agent(query=query, agent_config=config, tool_names=tool_names)

    time.sleep(0.5)
    print_agent_status(agent_id)
    server_wait_registered_agent(agent_id)

    server_continue_agent(agent_id, query='我刚才告诉你我叫什么？')

    print_agent_status(agent_id)

if __name__ == "__main__":
    main_test_server_start_agent()