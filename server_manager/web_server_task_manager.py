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
    # task的ID，目前为PREFIX+session_id(浏览器唯一), 后续可以为PREFIX+user_id+uuid
    task_id:str                     = ''

    # task对象，如agent_obj
    task_obj:Any                    = None

    # task的状态
    task_status:str                 = Web_Server_Task_Status.NOT_STARTED

    # task的output msg队列（用于stream输出信息给client）
    task_output_stream_queue_obj:queue.Queue  = field(default_factory=queue.Queue)

    # task的thinking msg队列（用于stream输出信息给client）
    task_thinking_stream_queue_obj:queue.Queue  = field(default_factory=queue.Queue)

    # task的log msg队列（用于stream输出信息给client）
    task_log_stream_queue_obj:queue.Queue  = field(default_factory=queue.Queue)

    # task返回的tool client data的msg队列（用于stream输出信息给client）
    task_tool_client_data_stream_queue_obj:queue.Queue  = field(default_factory=queue.Queue)

# 返回给client的data的格式
@dataclass
class Web_Client_Data_Type():
    TEXT:str        = 'text'
    IMAGE:str       = 'image'
    TABLE:str       = 'table'

# 返回给client的text data的格式
@dataclass
class Web_Client_Text_Data():
    content:str = None  # 如'my data'
    alignment:str='left'# 如'center'、'left'、'right'
    is_heading:str='false'
    font:str    = None  # 如'黑体, SimHei'、'宋体, SimSun'
    size:str    = None  # 如'22'、'12'
    color:str   = None  # 如'green'

# 返回给client的image data的格式
@dataclass
class Web_Client_Image_Data():
    content:str = None  # image data
    caption:str = None  # 如'xxx示意图'

# 返回给client的table data的格式
@dataclass
class Web_Client_Table_Data():
    content:str = None  # table data
    caption:str = None  # 如'xxx表'

# 返回给client的data
@dataclass
class Web_Client_Data():
    type:str        = None  # 如 Web_Client_Data_Type.TEXT
    data:str        = None  # 如 Web_Client_Text_Data、Web_Client_Image_Data、Web_Client_Table_Data

# 用于管理在web server侧运行的task
# 1、全系统唯一的task ID
# 2、task对应的obj，如agent_obj
# 3、task状态
# 4、task向前端输出的sse stream(通过queue实现)
class Web_Server_Task_Manager():
    # 用一个字典管理所有任务ID
    g_tasks_info_dict = {
        # 'task_id_xxx': Web_Server_Task_Info(xxx)
    }

    # 用于判断是否为local debug
    g_local_debug = False

    # 启动task
    @classmethod
    def start_task(cls, task_obj, session_id=None):
        if session_id is not None:
            session_id = Session_ID.PREFIX + session_id

            # client某浏览器重复执行了task
            if not Web_Server_Task_Manager.g_local_debug and session_id in Web_Server_Task_Manager.g_tasks_info_dict:
                if Web_Server_Task_Manager.g_tasks_info_dict[session_id].task_status == Web_Server_Task_Status.STARTED:
                    dyellow(f'Web_Server_Task_Manager.start_task(): 任务(task id: "{session_id}")已启动，不重复执行.')
                    task_id = session_id
                    return task_id
        else:
            dyellow(f'warning: Web_Server_Task_Manager.start_task()未采用session_id.')
            session_id = Session_ID.PREFIX + str(uuid.uuid4())

        # 创建消息队列用于stream
        task_output_stream_queue = queue.Queue()
        task_thinking_stream_queue = queue.Queue()
        task_log_stream_queue = queue.Queue()
        task_tool_client_data_stream_queue = queue.Queue()

        # 注册task info(其中还调用了set_output_stream_buf)
        Web_Server_Task_Manager.g_tasks_info_dict[session_id] = Web_Server_Task_Info(
            task_id=session_id,
            task_obj=task_obj,
            task_status=Web_Server_Task_Status.STARTED,
            task_output_stream_queue_obj=task_output_stream_queue,
            task_thinking_stream_queue_obj=task_thinking_stream_queue,
            task_log_stream_queue_obj=task_log_stream_queue,
            task_tool_client_data_stream_queue_obj=task_tool_client_data_stream_queue,
        )

        # task初始化
        if task_obj is not None:
            task_obj.init()
            try:
                # 设置stream输出的func
                task_obj.set_output_stream_buf(task_output_stream_queue.put)
                task_obj.set_thinking_stream_buf(task_thinking_stream_queue.put)
                task_obj.set_log_stream_buf(task_log_stream_queue.put)
                task_obj.set_tool_client_data_stream_buf(task_tool_client_data_stream_queue.put)
            except Exception as e:
                dred(f'Web_Server_Task_Manager.start_task() set_output_stream_buf()报错: "{e}"')

        # task启动
        def _run_task_thread():
            dgreen(f'Web_Server_Task_Manager(): task(id "{session_id}") 已启动...')
            if task_obj is not None:
                success = task_obj._run()

            # 测试stream
            if Web_Server_Task_Manager.g_local_debug:
                task_output_stream_queue.put('5')
                task_output_stream_queue.put('6')
                task_output_stream_queue.put('7')

            # 任务结束标志（重要！）
            task_output_stream_queue.put(None)

            Web_Server_Task_Manager.g_tasks_info_dict[session_id].task_status = Web_Server_Task_Status.FINISHED

            dgreen(f'Web_Server_Task_Manager(): task(id "{session_id}") 已完成.')

        thread = threading.Thread(target=_run_task_thread)
        thread.daemon = True
        thread.start()

        task_id = session_id
        return task_id

    # 获取task的llm结论输出stream(方便用户进行sse调用output、thinking、log等stream数据)
    @classmethod
    def get_task_output_sse_stream_gen(cls, task_id):
        if Web_Server_Task_Manager.g_local_debug:
            task_id = Session_ID.PREFIX + task_id

        # 获取该task的msg_queue
        task_output_stream_queue = Web_Server_Task_Manager.g_tasks_info_dict[task_id].task_output_stream_queue_obj

        # ======================================SSE封装=========================================
        # 大坑：典型的 SSE（Server-Sent Events）坑点，SSE 规范要求每个事件块之间都要用一个空行（也就是至少 \n\n）来分隔，否则前端的 SSE 解析往往会报错或无法成功解析
        # 因此，每一个f"data: {json.dumps({'message': chunk}, ensure_ascii=False)}\n\n"的最后必须要有\n\n才行，否则client会报错！！！
        def _generate():
            # 获取msg_queue的steam数据
            received = False
            while True:
                chunk = task_output_stream_queue.get()
                if chunk is None:  # 结束标志
                    break
                if chunk and not received:
                    received = True
                    dyellow(f'task output stream队列(id "{task_id}")'.center(80, '='))

                dyellow(chunk, end='', flush=True)
                yield f"data: {json.dumps({'message': chunk}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'[done]': True}, ensure_ascii=False)}\n\n"
            dyellow('\n')

            if received:
                dyellow(f'/task output stream队列(id "{task_id}")'.center(80, '-'))
        # ======================================SSE封装=========================================
        return _generate()

    # 获取task的llm的thinking输出stream
    @classmethod
    def get_task_thinking_sse_stream_gen(cls, task_id):
        if Web_Server_Task_Manager.g_local_debug:
            task_id = Session_ID.PREFIX + task_id

        # 获取该task的msg_queue
        task_thinking_stream_queue = Web_Server_Task_Manager.g_tasks_info_dict[task_id].task_thinking_stream_queue_obj

        # ======================================SSE封装=========================================
        # 大坑：典型的 SSE（Server-Sent Events）坑点，SSE 规范要求每个事件块之间都要用一个空行（也就是至少 \n\n）来分隔，否则前端的 SSE 解析往往会报错或无法成功解析
        # 因此，每一个f"data: {json.dumps({'message': chunk}, ensure_ascii=False)}\n\n"的最后必须要有\n\n才行，否则client会报错！！！
        def _generate():
            # 获取msg_queue的steam数据
            received = False
            while True:
                chunk = task_thinking_stream_queue.get()
                if chunk is None:  # 结束标志
                    break
                if chunk and not received:
                    received = True
                    dyellow(f'task thinking stream队列(id "{task_id}")'.center(80, '='))

                dyellow(chunk, end='', flush=True)
                yield f"data: {json.dumps({'message': chunk}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'[done]': True}, ensure_ascii=False)}\n\n"
            dyellow('\n')

            if received:
                dyellow(f'/task thinking stream队列(id "{task_id}")'.center(80, '-'))
        # ======================================SSE封装=========================================
        return _generate()

    # 获取task的log的输出(不是llm输出)
    @classmethod
    def get_task_log_sse_stream_gen(cls, task_id):
        if Web_Server_Task_Manager.g_local_debug:
            task_id = Session_ID.PREFIX + task_id

        # 获取该task的msg_queue
        task_log_stream_queue = Web_Server_Task_Manager.g_tasks_info_dict[task_id].task_log_stream_queue_obj

        # ======================================SSE封装=========================================
        # 大坑：典型的 SSE（Server-Sent Events）坑点，SSE 规范要求每个事件块之间都要用一个空行（也就是至少 \n\n）来分隔，否则前端的 SSE 解析往往会报错或无法成功解析
        # 因此，每一个f"data: {json.dumps({'message': chunk}, ensure_ascii=False)}\n\n"的最后必须要有\n\n才行，否则client会报错！！！
        def _generate():
            # 获取msg_queue的steam数据
            received = False
            while True:
                chunk = task_log_stream_queue.get()
                if chunk is None:  # 结束标志
                    break
                if chunk and not received:
                    received = True
                    dyellow(f'task log stream队列(id "{task_id}")'.center(80, '='))

                dyellow(chunk, end='', flush=True)
                yield f"data: {json.dumps({'message': chunk}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'[done]': True}, ensure_ascii=False)}\n\n"
            dyellow('\n')

            if received:
                dyellow(f'/task log stream队列(id "{task_id}")'.center(80, '-'))
        # ======================================SSE封装=========================================
        return _generate()

    # 获取task的tool的client data输出(不是llm输出)
    @classmethod
    def get_task_tool_client_data_sse_stream_gen(cls, task_id):
        if Web_Server_Task_Manager.g_local_debug:
            task_id = Session_ID.PREFIX + task_id

        # 获取该task的msg_queue
        task_tool_client_data_stream_queue = Web_Server_Task_Manager.g_tasks_info_dict[task_id].task_tool_client_data_stream_queue_obj

        # ======================================SSE封装=========================================
        # 大坑：典型的 SSE（Server-Sent Events）坑点，SSE 规范要求每个事件块之间都要用一个空行（也就是至少 \n\n）来分隔，否则前端的 SSE 解析往往会报错或无法成功解析
        # 因此，每一个f"data: {json.dumps({'message': chunk}, ensure_ascii=False)}\n\n"的最后必须要有\n\n才行，否则client会报错！！！
        def _generate():
            # 获取msg_queue的steam数据
            received = False
            while True:
                chunk = task_tool_client_data_stream_queue.get()
                if chunk is None:  # 结束标志
                    break
                if chunk and not received:
                    received = True
                    dyellow(f'task tool client data stream队列(id "{task_id}")'.center(80, '='))

                dyellow(chunk, end='', flush=True)
                yield f"data: {json.dumps({'message': chunk}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'[done]': True}, ensure_ascii=False)}\n\n"
            dyellow('\n')

            if received:
                dyellow(f'/task tool client data stream队列(id "{task_id}")'.center(80, '-'))
        # ======================================SSE封装=========================================
        return _generate()

def main():
    Web_Server_Task_Manager.g_local_debug = True

    session_id ='329'
    Web_Server_Task_Manager.start_task(task_obj=None, session_id=session_id)
    print()
    print(Web_Server_Task_Manager.g_tasks_info_dict[Session_ID.PREFIX+session_id])
    print()
    gen = Web_Server_Task_Manager.get_task_output_sse_stream_gen(task_id=session_id)
    for chunk in gen:
        print(chunk)
        # print(chunk, end='', flush=True)

if __name__ == "__main__":
    main()