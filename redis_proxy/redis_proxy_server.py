import config

from utils.task import Status
from redis_client import Redis_Client
from config import dred,dgreen
from tools.llm.api_client import LLM_Client
import time

from redis_proxy.custom_command.protocol import server_add_task, server_invoking_command
from redis_proxy.thread import Task_Worker_Thread, Redis_Proxy_Server_Thread

from redis_proxy.custom_command.llm.protocol import Redis_Proxy_Command_LLM

from redis_proxy.custom_command.llm.servant import llm_servant

def Redis_Proxy_Server_Callback(out_task_info_must_be_here):
    thread_status = out_task_info_must_be_here

    def cancel():
        dred(f"Redis Proxy Server ({thread_status['task_name']}) cancelling...")

    def __pop_stream(key):
        return s_redis_client.pop_stream(key)


    # 注册各种类型的任务
    def __add_task(inout_register_data, task_id, task_type):
        server_add_task(inout_register_data, task_id, task_type)

    # 响应client的new task
    def polling_new_tasks():
        # print(f's_redis_proxy_server_data: {s_redis_proxy_server_data}')
        dict_list = __pop_stream(key='Task_Register')
        for dict in dict_list:
            # print(f'new task dict: {dict}')
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

                __add_task(inout_register_data=s_redis_proxy_server_data[cid], task_id=tid, task_type=ttype)

    # 执行command
    def __exec_command(**arg_dict):
        server_invoking_command(s_redis_proxy_server_data, s_redis_client, **arg_dict)

    # 响应client某task的command
    def polling_task_commands():
        for k,v in s_redis_proxy_server_data.items():
            # 所有client_id
            for k1,v1 in v.items():
                # 所有task_id
                task_id = k1

                # 查询该task下的command
                stream_key = f'Task_{task_id}_Command'
                dict_list = __pop_stream(key=stream_key)

                # 执行所有command
                for command_para_dict in dict_list:
                    __exec_command(**command_para_dict)

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

def server_init():
    global s_redis_proxy_server_data, s_redis_client, s_redis_proxy_server_thread

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

    IS_SERVER = True
    if IS_SERVER:
        # 启动 Redis Task Server
        s_redis_client = Redis_Client(host='192.168.124.33', port=8010)  # ubuntu-server
        # redis清空所有数据
        s_redis_client.flushall()

        # s_redis_client = Redis_Client(host='localhost', port=6379)  # win-server
        s_redis_proxy_server_thread = Redis_Proxy_Server_Thread()
        s_redis_proxy_server_thread.init(Redis_Proxy_Server_Callback)
        # s_redis_task_server.init(Redis_Task_Server_Callback, in_timeout=5)
        s_redis_proxy_server_thread.start()

def main():
    server_init()
    while(1):
        time.sleep(1)

if __name__ == "__main__":
    main()
