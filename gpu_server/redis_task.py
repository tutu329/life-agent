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

@dataclass
class Redis_Task_LLM_Data:
    task_type:str = str(Redis_Task_Type.LLM)     #任务类型

    url:str = ''
    history:bool = True
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


# client，仅通过redis发送启动任务的消息，所有任务由Redis_Task_Server后台异步解析和处理
@singleton
class Redis_Task_Client():
    def __init__(self):
        pass

    def add_llm_task(
            self,
            url='',
            history = True,
            max_new_tokens = 512,
            temperature = 0.7,
            api_key = 'empty',
    ):
        client = Redis_Client(host='localhost', port=6379)  # win-server

        data = Redis_Task_LLM_Data()
        data.task_type = str(Redis_Task_Type.LLM)
        data.url = url
        data.history = history
        data.max_new_tokens = max_new_tokens
        data.temperature = temperature
        data.api_key = api_key

        task_id = 'llm_task_' + str(uuid.uuid4())
        print(f'add_llm_task() task_id: {task_id}')
        client.add_stream(task_id, data=asdict(data))

        return task_id

    def llm_ask(self, task_id, question):
        client = Redis_Client(host='localhost', port=6379)  # win-server

        data = LLM_Ask_Data()
        data.question = question

        client.add_stream(task_id, data=asdict(data))

# 被Redis_Task_Server调用的worker，用于启动llm、t2i、tts等异步任务
class Task_Worker(Task_Base):
    def __init__(self):
        super().__init__()

    def init(self,
             in_callback_func,
             *in_callback_func_args,
             in_name='task_worker_'+str(uuid.uuid4()),
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
class Redis_Task_Server(Task_Base):
    def __init__(self):
        super().__init__()

    def init(self,
             in_callback_func,
             *in_callback_func_args,
             in_name='redis_task_server_'+str(uuid.uuid4()),
             in_timeout=None,    # timeout秒之后，设置cancel标识
             in_streamlit=False,
             **in_callback_func_kwargs
            ):
        if not self.inited:
            dgreen(f'Redis Task Server (id="{in_name}") started.')

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

def Redis_Task_Server_Callback(out_task_info_must_be_here):
    rt_status = out_task_info_must_be_here

    def cancel():
        dred(f"Redis Task Server ({rt_status['task_name']}) cancelling...")

    def llm_task(input):
        llm = LLM_Client(url='http://192.168.124.33:8001/v1')
        llm.ask_prepare(in_question=input)
        llm.get_answer_and_sync_print()

    def task(stream_last_id):
        inout_list = []
        last_id = None
        if stream_last_id is not None:
            last_id = s_redis_client.pop_stream('redis_task', inout_data_list=inout_list, last_id=stream_last_id)
            for item in inout_list:
                print(f'item: "{item}')
                if item['task_type']==str(Redis_Task_Type.LLM):
                    llm_task(input=item['task_input'])
        return last_id

    last_id = '0-0'
    last_valid_id = '0-0'  # 查询到最后一个msg后，redis会返回None而不是最后一个msg的id
    while True:
        if rt_status['status']==Status.Cancelling:
            # cancel中
            cancel()
            dred(f"Redis Task Server ({rt_status['task_name']}) cancelled")
            break

        # print(f'last_id: {last_id}')
        last_id = task(last_id)

        # 查询到最后一个msg后，redis会返回None而不是最后一个msg的id
        if last_id is not None:
            last_valid_id = last_id
        else:
            # 返回None，这里改为最后一个msg的id
            last_id = last_valid_id

        # time.sleep(1)
        time.sleep(config.Global.redis_task_server_sleep_time)

# IS_SERVER = False
IS_SERVER = True
if IS_SERVER:
    # 启动 Redis Task Server
    s_redis_client = Redis_Client(host='192.168.124.33', port=8010)  # ubuntu-server
    # s_redis_client = Redis_Client(host='localhost', port=6379)  # win-server
    s_redis_task_server = Redis_Task_Server()
    s_redis_task_server.init(Redis_Task_Server_Callback)
    # s_redis_task_server.init(Redis_Task_Server_Callback, in_timeout=5)
    s_redis_task_server.start()

def main():
    while(1):
        time.sleep(1)

if __name__ == "__main__":
    main()
