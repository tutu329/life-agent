from singleton import singleton
from enum import Enum, unique
from dataclasses import dataclass, asdict, field
import uuid
import uuid

from redis_client import Redis_Client
# from redis_proxy.redis_proxy_server import Redis_Task_Type, Redis_Task_LLM_Data, LLM_Ask_Data

from config import dred, dgreen
from redis_proxy.protocol import Redis_Task_Type
from redis_proxy.protocol import Redis_LLM_Command


s_redis = Redis_Client(host='192.168.124.33', port=8010)  # ubuntu-server
# s_redis = Redis_Client(host='localhost', port=6379)  # win-server

# client，仅通过redis发送启动任务的消息，所有任务由Redis_Task_Server后台异步解析和处理
@singleton
class Redis_Proxy_Client():
    def __init__(self):
        self.client_id = 'Client_' + str(uuid.uuid4())

    # 向server发送一个消息，在server构造一个task
    def new_task(
            self,
            task_type:str,                  # task类型
    )->str:                                 # 返回task_id
        task_id = 'Task_' + str(uuid.uuid4())

        s_redis.add_stream(
            stream_key='Task_Register',
            data={
                'client_id': self.client_id,
                'task_type': str(task_type),
                'task_id': task_id,
            },
        )

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
            'client_id': self.client_id,
            'task_id': task_id,
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
        status = s_redis.get_string(key=key)

        return status

    # 返回task的result数据
    def get_result_gen(self, task_id):       # 由new_task()返回的唯一的task_id，作为llm-obj等对象的容器id
        # 返回stream_key为'Task_xxxid_Result'（该数据由server填充）的最新数据
        stream_key = f'Task_{task_id}_Result'

        # 读取最新stream数据
        while True:
            result_dict = s_redis.pop_stream(stream_key=stream_key)
            for item in result_dict:
                if item['status'] != 'completed':
                    yield item['chunk']
                else:
                    return


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