import config
from singleton import singleton

from enum import Enum, unique
from dataclasses import dataclass, asdict, field
from typing import List, Any

from utils.task import Task_Base, Status
from redis_client import Redis_Client
from config import dred,dgreen

from tools.llm.api_client import LLM_Client

import uuid,time

@unique
class Redis_Task_Type(Enum):
    LLM = 'LLM'
    T2I = 'T2I'
    TTS = 'TTS'

@unique
class Redis_LLM_Command(Enum):
    INIT = 'INIT'
    START = 'START'
    CANCEL = 'CANCEL'
    ASK = 'ASK'




@dataclass
class Redis_Task_LLM_Data:
    task_type:str = str(Redis_Task_Type.LLM)     #任务类型

    url:str = ''
    history:int = int(True)
    max_new_tokens:int = 512
    temperature:float = 0.7
    api_key:str = 'empty'

@dataclass
class LLM_Ask_Data:
    question:str = ''

    temperature:Any = None
    max_new_tokens:Any = None
    clear_history:Any = None
    stream:Any = None
    stops:Any = None
    # stops:List[str] = field(default_factory=list)
    system_prompt:Any = None

# 被Redis_Task_Server调用的worker，用于启动llm、t2i、tts等异步任务
class Task_Worker_Thread(Task_Base):
    def __init__(self):
        super().__init__()

    def init(self,
             in_callback_func,
             *in_callback_func_args,
             in_name='Task_Worker_'+str(uuid.uuid4()),
             in_timeout=None,    # timeout秒之后，设置cancel标识
             in_streamlit=False,
             **in_callback_func_kwargs
            ):
        if not self.inited:
            dgreen(f'Task Worker (id="{in_name}") started.')

        super().init(
             in_callback_func,
             *in_callback_func_args,
             in_name=in_name,
             in_timeout=in_timeout,
             in_streamlit=in_streamlit,
             **in_callback_func_kwargs
        )

    def start(self):
        super().start()

@singleton
class Redis_Proxy_Server_Thread(Task_Base):
    def __init__(self):
        super().__init__()

    def init(self,
             in_callback_func,
             *in_callback_func_args,
             in_name='Redis_Proxy_Server_'+str(uuid.uuid4()),
             in_timeout=None,    # timeout秒之后，设置cancel标识
             in_streamlit=False,
             **in_callback_func_kwargs
            ):
        if not self.inited:
            dgreen(f'Redis Proxy Server (id="{in_name}") started.')

        super().init(
             in_callback_func,
             *in_callback_func_args,
             in_name=in_name,
             in_timeout=in_timeout,
             in_streamlit=in_streamlit,
             **in_callback_func_kwargs
        )

    def start(self):
        super().start()

# def Redis_Proxy_Server_Callback1(out_task_info_must_be_here):
#     rt_status = out_task_info_must_be_here
#
#     def cancel():
#         dred(f"Redis Proxy Server ({rt_status['task_name']}) cancelling...")
#
#     def llm_task(input):
#         llm = LLM_Client(url='http://192.168.124.33:8001/v1')
#         llm.ask_prepare(in_question=input)
#         llm.get_answer_and_sync_print()
#
#     def task(stream_last_id):
#         inout_list = []
#         last_id = None
#         if stream_last_id is not None:
#             last_id = s_redis_client.pop_stream('redis_task', inout_data_list=inout_list, last_id=stream_last_id)
#             for item in inout_list:
#                 print(f'item: "{item}')
#                 if item['task_type']==str(Redis_Task_Type.LLM):
#                     llm_task(input=item['task_input'])
#         return last_id
#
#     last_id = '0-0'
#     last_valid_id = '0-0'  # 查询到最后一个msg后，redis会返回None而不是最后一个msg的id
#     while True:
#         if rt_status['status']==Status.Cancelling:
#             # cancel中
#             cancel()
#             dred(f"Redis Task Server ({rt_status['task_name']}) cancelled")
#             break
#
#         # print(f'last_id: {last_id}')
#         last_id = task(last_id)
#
#         # 查询到最后一个msg后，redis会返回None而不是最后一个msg的id
#         if last_id is not None:
#             last_valid_id = last_id
#         else:
#             # 返回None，这里改为最后一个msg的id
#             last_id = last_valid_id
#
#         # time.sleep(1)
#         time.sleep(config.Global.redis_task_server_sleep_time)

# IS_SERVER = False

s_redis_proxy_server_data = {
    # 'client-id1' : {
    #     'task-id1' : {
    #         'task_type' : str(Redis_Task_Type.LLM),
    #         'task_status' : '',
    #         'task_system' : [
    #             {
    #                 'obj': llm_client,
    #                 'thread': llm_client_thread,
    #             },
    #             {
    #                 'obj': tts_client,
    #                 'thread': tts_client_thread,
    #             },
    #         ],
    #     },
    #     'task-id2' : {
    #         'task_type' : str(Redis_Task_Type.LLM),
    #         'task_status': '',
    #     },
    # },
    # 'client-id2' : {
    # },
}

def Redis_Proxy_Server_Callback(out_task_info_must_be_here):
    thread_status = out_task_info_must_be_here

    def cancel():
        dred(f"Redis Proxy Server ({thread_status['task_name']}) cancelling...")

    def pop_stream(key):
        return s_redis_client.pop_stream(key)


    # 注册各种类型的任务
    def add_task(inout_register_data, task_id, task_type):
        assert task_id not in inout_register_data

        data = None
        if task_type==str(Redis_Task_Type.LLM):
            data = {
                'task_type': task_type,
                'task_status': '',
                'task_system': [
                    {
                        'obj': None,
                        'thread': None,
                    },
                    # {
                    #     'obj': tts_client,
                    #     'thread': tts_client_thread,
                    # },
                ],
            }

        inout_register_data[task_id] = data


    # 响应client的new task
    def polling_new_tasks():
        print(f's_redis_proxy_server_data: {s_redis_proxy_server_data}')
        dict_list = pop_stream(key='Task_Register')
        for dict in dict_list:
            print(f'new task dict: {dict}')
            # {'client_id': 'Client_7b8024f3-f88c-4756-97c3-c583252ce6e5', 'task_type': 'Redis_Task_Type.LLM', 'task_id': 'Task_41158011-e11e-4a3e-84f4-38fd87fba71d'}

            if 'client_id' in dict and 'task_type' in dict and 'task_id' in dict:
                cid = dict['client_id']
                tid = dict['task_id']
                ttype = dict['task_type']
                if cid in s_redis_proxy_server_data:
                    # 已有该client数据
                    pass
                else:
                    # 没有该client数据
                    s_redis_proxy_server_data[cid] = {}

                add_task(inout_register_data=s_redis_proxy_server_data[cid], task_id=tid, task_type=ttype)





    # 响应client某task的command
    def polling_task_commands():
        pass

    # Redis Proxy Server 主循环
    while True:
        if thread_status['status']==Status.Cancelling:
            # cancel中
            cancel()
            dred(f"Redis Task Server ({thread_status['task_name']}) cancelled")
            break

        polling_new_tasks()
        polling_task_commands()

        time.sleep(2)
        # time.sleep(config.Global.redis_proxy_server_sleep_time)

IS_SERVER = True
if IS_SERVER:
    # 启动 Redis Task Server
    s_redis_client = Redis_Client(host='192.168.124.33', port=8010)  # ubuntu-server
    # s_redis_client = Redis_Client(host='localhost', port=6379)  # win-server
    s_redis_proxy_server_thread = Redis_Proxy_Server_Thread()
    s_redis_proxy_server_thread.init(Redis_Proxy_Server_Callback)
    # s_redis_task_server.init(Redis_Task_Server_Callback, in_timeout=5)
    s_redis_proxy_server_thread.start()

def main():
    while(1):
        time.sleep(1)

if __name__ == "__main__":
    main()
