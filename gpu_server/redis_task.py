import config
from singleton import singleton

from enum import Enum, unique
from dataclasses import dataclass, asdict, field

from utils.task import Task_Base, Status
from redis_client import Redis_Client
from config import dred,dgreen

import uuid,time

@unique
class Redis_Task_Type(Enum):
    LLM = 'LLM'
    T2I = 'T2I'
    TTS = 'TTS'

@dataclass
class Redis_Task_Data:
    task_type:str = str(Redis_Task_Type.LLM)     #任务类型
    task_input:str = ''                                 #任务输入

class Redis_Task_Client():
    def __init__(self):
        pass

    def add_llm_task(self, input):
        client = Redis_Client(host='localhost', port=6379)  # win-server
        data = Redis_Task_Data()
        data.task_type = str(Redis_Task_Type.LLM)
        data.task_input = input
        print(f'add_llm_task() input: {input}')
        client.add_stream('redis_task', data=asdict(data))

@singleton
class Redis_Task_Server(Task_Base):
    def __init__(self):
        super().__init__()

    def init(self,
             in_callback_func,
             *in_callback_func_args,
             in_name='redis_task_'+str(uuid.uuid4()),
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

def redis_test():
    client = Redis_Client(host='localhost', port=6379)  # win-server

    # client = Redis_Client(host='192.168.124.33')  # ubuntu-server
    d = {
        'aa':22,
        'bb':11,
    }
    client.set_dict('msg', d)
    print(client.get_dict('msg'))
    print('ssss')

    inout_list1 = []
    inout_list2 = []
    client.add_stream('test_stream', data={'name':'jack', 'age':37})
    last1 = client.pop_stream('test_stream', inout_data_list=inout_list1)
    last2 = client.pop_stream('test_stream', use_byte=False, inout_data_list=inout_list2,  last_id='1718178990332-0', count=2)

    print(f'last1: {last1}')
    print(f'inout_list1: "{inout_list1}')
    print(f'last2: {last2}')
    print(f'inout_list2: "{inout_list2}')

def Redis_Task_Server_Callback(out_task_info_must_be_here):
    rt_status = out_task_info_must_be_here

    def cancel():
        dred(f"Redis Task Server ({rt_status['task_name']}) cancelling...")

    def task(stream_last_id):
        inout_list = []
        last_id = None
        if stream_last_id is not None:
            last_id = s_redis_client.pop_stream('redis_task', inout_data_list=inout_list, last_id=stream_last_id)
            for item in inout_list:
                print(f'item: "{item}')
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
    s_redis_client = Redis_Client(host='localhost', port=6379)  # win-server
    s_redis_task_server = Redis_Task_Server()
    s_redis_task_server.init(Redis_Task_Server_Callback)
    # s_redis_task_server.init(Redis_Task_Server_Callback, in_timeout=5)
    s_redis_task_server.start()


def Example_Callback(out_task_info_must_be_here, num, num2):
    i=num
    while True:
        i += 1
        if out_task_info_must_be_here['status']==Status.Cancelling:
             print(f"{out_task_info_must_be_here['task_name']} cancelled")
             break
        print(i)
        # print(out_task_info_must_be_here)
        time.sleep(1)

def main():
    # t = Redis_Task_Server()
    # t.init(Example_Callback, in_timeout=3, num=100, num2=300)
    # t.start()
    while(1):
        time.sleep(1)

if __name__ == "__main__":
    main()
    # redis_test()