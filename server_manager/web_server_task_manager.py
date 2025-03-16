from dataclasses import dataclass, field
from typing import Any

import queue
import uuid
import threading
import json

from pprint import pprint

from config import dred, dgreen, dblue, dcyan, dyellow

@dataclass
class Session_ID():
    PREFIX:str = 'session_id_'

@dataclass
class Web_Server_Task_Status():
    NOT_STARTED:str = 'not started'
    STARTED:str     = 'started'
    FINISHED:str    = 'finished'

@dataclass
class Web_Server_Task_Info():
    task_id:str                     = ''                                                        # task的ID
    task_obj:Any                    = None                                                      # 无类型限制，使用Any
    task_status:str                 = Web_Server_Task_Status.NOT_STARTED                        # task的状态
    task_stream_queue_obj:queue.Queue  = field(default_factory=queue.Queue)                     # task的msg队列（用于stream输出信息给client）

class Web_Server_Task_Manager():
    # 用一个字典管理所有任务ID -> 消息队列(或其他数据结构)
    g_tasks_info_dict = {
        # 'task_id_xxx': Agent_Task_Info(xxx)
    }

    g_local_debug = False

    # 启动task
    @classmethod
    def start_task(cls, task_obj, session_id=None):
        if session_id is not None:
            session_id = Session_ID.PREFIX + session_id
        else:
            dyellow(f'warning: Web_Server_Task_Manager.start_task()未采用session_id.')
            session_id = Session_ID.PREFIX + str(uuid.uuid4())

        # 创建消息队列用于stream
        task_stream_queue = queue.Queue()

        # 注册task info
        Web_Server_Task_Manager.g_tasks_info_dict[session_id] = Web_Server_Task_Info(
            task_id=session_id,
            task_obj=task_obj,
            task_status=Web_Server_Task_Status.STARTED,
            task_stream_queue_obj=task_stream_queue,
        )

        # task初始化
        if task_obj is not None:
            task_obj.init()
            try:
                # 设置最终结果stream输出的func
                task_obj.set_output_stream_buf(task_stream_queue.put)
            except Exception as e:
                dred(f'Web_Server_Task_Manager.start_task() set_output_stream_buf()报错: "{e}"')

        # task启动
        def _run_task_thread():
            dgreen(f'Web_Server_Task_Manager(): task(id "{session_id}") 已启动...')
            if task_obj is not None:
                success = task_obj.run()

            # 测试stream
            if Web_Server_Task_Manager.g_local_debug:
                task_stream_queue.put('5')
                task_stream_queue.put('6')
                task_stream_queue.put('7')

            # 任务结束标志（重要！）
            task_stream_queue.put(None)

            dgreen(f'Web_Server_Task_Manager(): task(id "{session_id}") 已完成.')

        thread = threading.Thread(target=_run_task_thread)
        thread.daemon = True
        thread.start()

        task_id = session_id
        return task_id

    # 获取task的输出stream(用户client的sse stream调用)
    @classmethod
    def get_task_sse_stream_gen(cls, task_id):
        if Web_Server_Task_Manager.g_local_debug:
            task_id = Session_ID.PREFIX + task_id

        # 获取该task的msg_queue
        task_stream_queue = Web_Server_Task_Manager.g_tasks_info_dict[task_id].task_stream_queue_obj

        def _generate():
            # 获取msg_queue的steam数据
            received = False
            while True:
                chunk = task_stream_queue.get()
                if chunk is None:  # 结束标志
                    break
                if chunk and not received:
                    received = True
                    dyellow(f'task stream队列(id "{task_id}")'.center(80, '='))

                dyellow(chunk, end='', flush=True)
                yield f"data: {json.dumps({'message': chunk}, ensure_ascii=False)}"

            yield f"data: {json.dumps({'[done]': True}, ensure_ascii=False)}"
            dyellow('\n')

            if received:
                dyellow(f'/task stream队列(id "{task_id}")'.center(80, '-'))

        return _generate()

def main():
    Web_Server_Task_Manager.g_local_debug = True

    session_id ='329'
    Web_Server_Task_Manager.start_task(task_obj=None, session_id=session_id)
    print()
    print(Web_Server_Task_Manager.g_tasks_info_dict[Session_ID.PREFIX+session_id])
    print()
    gen = Web_Server_Task_Manager.get_task_sse_stream_gen(task_id=session_id)
    for chunk in gen:
        print(chunk)
        # print(chunk, end='', flush=True)

if __name__ == "__main__":
    main()