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

# 注册各种类型的任务( [1]task <-> [n]command )
def server_add_task(inout_client_data, task_id, task_type):
    assert task_id not in inout_client_data

    # data = None
    # if task_type == str(Redis_Task_Type.LLM):
    data = {
        'task_type': task_type,
        'task_status_key': f'Task_{task_id}_Status',
        'task_result_key': f'Task_{task_id}_Result',
        'command_system': [
            {
                'obj': None,
                'thread': None,
            },
        ],
        # 由于某一类command对应n个bridge，因此bridge不是某个task或者某个task下的某个command的一部分
        # 因此bridge_system是client的一部分
        # 'bridge_system':[
        #     {
        #         'obj': None,
        #         'thread': None,
        #     },
        # ],
    }


    inout_client_data[task_id] = data

