from enum import Enum, unique

from config import dred, dgreen
import config

# from redis_proxy.command.llm.servant import llm_servant

# from redis_proxy.command.thread import Redis_Proxy_Server_Thread
# from import Redis_Proxy_Server_Callback
# from redis_proxy.redis_proxy_client import Redis_Client

# s_redis_proxy_server_data = {
#     # 'client-id1' : {
#     #     'task-id1' : {
#     #         'task_type' : str(Redis_Task_Type.LLM),
#     #         'task_status' : '',
#     #         'task_system' : [
#     #             {
#     #                 'obj': llm_client,
#     #                 'thread': llm_client_thread,
#     #             },
#     #             {
#     #                 'obj': tts_client,
#     #                 'thread': tts_client_thread,
#     #             },
#     #         ],
#     #     },
#     #     'task-id2' : {
#     #         'task_type' : str(Redis_Task_Type.LLM),
#     #         'task_status': '',
#     #     },
#     # },
#     # 'client-id2' : {
#     # },
# }

# IS_SERVER = True
# if IS_SERVER:
#     # 启动 Redis Task Server
#     s_redis_client = Redis_Client(host='192.168.124.33', port=8010)  # ubuntu-server
#     # redis清空所有数据
#     s_redis_client.flushall()
#
#     # s_redis_client = Redis_Client(host='localhost', port=6379)  # win-server
#     s_redis_proxy_server_thread = Redis_Proxy_Server_Thread()
#     s_redis_proxy_server_thread.init(Redis_Proxy_Server_Callback)
#     # s_redis_task_server.init(Redis_Task_Server_Callback, in_timeout=5)
#     s_redis_proxy_server_thread.start()

@unique
class Redis_Task_Type(Enum):
    LLM = 'LLM'
    T2I = 'T2I'
    TTS = 'TTS'

def invoking(**arg_dict):
    command = arg_dict['command']

    if 'Redis_Proxy_Command_LLM' in command:
        llm_servant()

def add_task(inout_register_data, task_id, task_type):
    assert task_id not in inout_register_data

    data = None
    if task_type == str(Redis_Task_Type.LLM):
        data = {
            'task_type': task_type,
            'task_status_key': f'Task_{task_id}_Status',
            'task_result_key': f'Task_{task_id}_Result',
            'task_system': [
                {
                    'obj': None,
                    'thread': None,
                    # 'obj': LLM_Client(
                    #     url=config.Global.llm_url,
                    #     history=True,
                    #     max_new_tokens=config.Global.llm_max_new_tokens,
                    #     temperature=config.Global.llm_temperature,
                    # ),
                    # 'thread': Task_Worker_Thread(),
                },
                # {
                #     'obj': tts_client,
                #     'thread': tts_client_thread,
                # },
            ],
        }

    inout_register_data[task_id] = data

