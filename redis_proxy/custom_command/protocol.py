from enum import Enum, unique
from redis_proxy.custom_command.llm.servant import llm_servant
from redis_proxy.custom_command.t2i.servant import t2i_servant

from config import dred, dgreen

@unique
class Redis_Task_Type(Enum):
    LLM = 'LLM'
    T2I = 'T2I'
    TTS = 'TTS'

# 执行command
def server_invoking_command(s_redis_proxy_server_data, s_redis_client, **arg_dict):
    command = arg_dict['command']

    dgreen(f'server_invoking_command() invoked.')
    # dgreen(f'command: {command}')
    # dgreen(f'arg_dict:')
    for k, v in arg_dict.items():
        dgreen(f'\t {k}: {v}')

    if 'Redis_Proxy_Command_LLM' in command:
        llm_servant(s_redis_proxy_server_data, s_redis_client, **arg_dict)

    if 'Redis_Proxy_Command_T2I' in command:
        t2i_servant(s_redis_proxy_server_data, s_redis_client, **arg_dict)

# 注册各种类型的任务
def server_add_task(inout_client_data, task_id, task_type):
    assert task_id not in inout_client_data

    # data = None
    # if task_type == str(Redis_Task_Type.LLM):
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

    inout_client_data[task_id] = data
