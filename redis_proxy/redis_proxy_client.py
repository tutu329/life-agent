from singleton import singleton
from enum import Enum, unique
from dataclasses import dataclass, asdict, field
import uuid
import uuid

from redis_client import Redis_Client
from redis_proxy.redis_proxy_server import Redis_Task_Type, Redis_Task_LLM_Data, LLM_Ask_Data

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