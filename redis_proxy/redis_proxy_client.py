from singleton import singleton
from enum import Enum, unique
from dataclasses import dataclass, asdict, field
import uuid
import uuid

from redis_client import Redis_Client
from redis_proxy.redis_proxy_server import Redis_Task_Type, Redis_Task_LLM_Data, LLM_Ask_Data

from config import dred, dgreen

s_redis = Redis_Client(host='192.168.124.33', port=8010)  # ubuntu-server
# s_redis = Redis_Client(host='localhost', port=6379)  # win-server

# client，仅通过redis发送启动任务的消息，所有任务由Redis_Task_Server后台异步解析和处理
@singleton
class Redis_Proxy_Client():
    def __init__(self):
        self.task_result_stream_last_id = {     # 用于存放返回数据的stream_id指针
            # stream_key1: result_stream_id1,
            # stream_key2: result_stream_id2,
        }

    # 向server发送一个消息，在server构造一个task
    def new_task(
            self,
            task_type:str,                  # task类型
    )->str:                                 # 返回task_id
        task_id = 'Task_' + str(uuid.uuid4())

        s_redis.add_stream(
            stream_key='Task_Register',
            data={
                'task_type': str(task_type),
                'task_id': task_id,
            },
        )

        # 初始化task_id对应的result_stream_last_id
        stream_key = f'Task_{task_id}_Result'
        self.task_result_stream_last_id[stream_key] = None

        return task_id

    # 向server发送一个消息，在server执行某task的一个command
    def send_command(
            self,
            task_id,        # 由new_task()返回的唯一的task_id，作为llm-obj等对象的容器id
            command:str,    # 例如：str(Redis_LLM_Command.INIT)
            **arg_dict,     # 例如：{'key': 'value', 'key2': 'value2'}
    ):
        # 封装redis的data
        data = {
            'command': command,
        }
        # redis必须将arg_dict的item加到data中，而不能嵌套dict
        for k, v in arg_dict.items():
            data[k] = v

        # 发送command
        s_redis.add_stream(
            stream_key=f'Task_{task_id}_Command',   # 与task_id一一对应的stream_key
            data=data,
        )

    # 返回task的status
    def get_status(self, task_id):
        # 返回key为'Task_xxxid_Status'（该数据由server填充）的最新数据
        key = f'Task_{task_id}_Status'
        status_dict = s_redis.get_dict(key=key)     # status_dict为{'status': 'xxx'}

        if 'status' in status_dict:
            return status_dict['status']
        else:
            return None

    # 返回task的result数据
    def get_result(self, task_id,        # 由new_task()返回的唯一的task_id，作为llm-obj等对象的容器id
    )->str:                 # 返回的数据
        # 返回stream_key为'Task_xxxid_Result'（该数据由server填充）的最新数据

        dred(f'get_result()之前：self.task_result_stream_last_id: {self.task_result_stream_last_id}')

        stream_key = f'Task_{task_id}_Result'

        # 读取最新stream数据
        inout_data_list = []
        if stream_key in  self.task_result_stream_last_id and self.task_result_stream_last_id[stream_key] is not None:
            last_stream_id = self.task_result_stream_last_id[stream_key]
        else:
            last_stream_id = '0-0'
        last_stream_id = s_redis.pop_stream(stream_key=stream_key, inout_data_list=inout_data_list, use_byte=False, last_id=last_stream_id)

        # stream last_id指针放在最后，如没有新的数据则不变
        if last_stream_id is not None:
            self.task_result_stream_last_id[stream_key] = last_stream_id

        dgreen(f'get_result()之后：self.task_result_stream_last_id: {self.task_result_stream_last_id}')

        if inout_data_list:
            return inout_data_list[-1]
        else:
            return None



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
        # client = Redis_Client(host='192.168.124.33', port=8010)  # ubuntu-server
        client = Redis_Client(host='localhost', port=6379)  # win-server

        data = Redis_Task_LLM_Data()
        data.task_type = str(Redis_Task_Type.LLM)
        data.url = url
        data.history = int(history)
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