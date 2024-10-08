import uuid
from enum import Enum, unique
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any

from redis_proxy.custom_command.llm.servant import llm_servant, call_llm_servant
from redis_proxy.custom_command.t2i.servant import t2i_servant, call_t2i_servant

from config import dred, dblue, dgreen

@unique
class Redis_Task_Type(Enum):
    LLM = 'LLM'
    T2I = 'T2I'
    TTS = 'TTS'

@dataclass
class Client_New_Command_Paras:    # new task是顶层命令，不适合放在custom_command下面（与自定义的功能无关）
    client_id: str = ''     # client_id由client提供，可以是str(uuid.uuid4())
    task_id: str = ''       # task_id由client提供，可以是str(uuid.uuid4())
    command_id: str = ''    # command_id由client提供，可以是str(uuid.uuid4())
    command: str = ''  # Redis_Proxy_Command_LLM


def call_custom_command(
        task_type,
        command,
        task_obj,
        output_callback,    # output_callback(output_string:str, use_byte:bool)
        finished_callback,  # finished_callback()
        **command_paras_dict
):  # 必须返回new_task_obj或task_obj_already_exists
    # LLM
    if str(Redis_Task_Type.LLM) in task_type:
        return call_llm_servant(
            command=command,
            task_obj_already_exists=task_obj,
            output_callback=output_callback,
            finished_callback=finished_callback,
            **command_paras_dict
        )
    # T2I
    if str(Redis_Task_Type.T2I) in task_type:
        return call_t2i_servant(
            command=command,
            task_obj_already_exists=task_obj,
            output_callback=output_callback,
            finished_callback=finished_callback,
            **command_paras_dict
        )
# 执行command
def server_invoking_command(s_redis_proxy_server_data, s_redis_client, task_id, client_id, command, command_id, **arg_dict):
    cid = client_id
    tid = task_id
    command = command

    dgreen(f'server_invoking_command() invoked.')
    # dgreen(f'command: {command}')
    # dgreen(f'arg_dict:')
    for k, v in arg_dict.items():
        dgreen(f'\t {k}: {v}')

    cmd_id = command_id
    # cmd_id = str(uuid.uuid4())
    cmd_data = s_redis_proxy_server_data.clients[cid].tasks[tid].commands
    # cmd_data = s_redis_proxy_server_data[cid][tid]['command_system']
    status_key = f'Task_{tid}_Status_CMD_{cmd_id}'
    result_key = f'Task_{tid}_Result_CMD_{cmd_id}'
    # ===========添加新的cmd的信息===========
    # cmd_data['obj'] = None
    # cmd_data['thread'] = None
    # cmd_data['returned_cmd_ids'] = None
    cmd_data[cmd_id] = {
        'cmd_status_key': status_key,
        'cmd_result_key': result_key,
    }
    # ===================================

    if 'Redis_Proxy_Command_LLM' in command:
        llm_servant(s_redis_proxy_server_data, s_redis_client, status_key, result_key, task_id, client_id, command, command_id, **arg_dict)

    if 'Redis_Proxy_Command_T2I' in command:
        t2i_servant(s_redis_proxy_server_data, s_redis_client, status_key, result_key, cmd_id,  **arg_dict)

# 注册各种类型的任务( [1]task <-> [n]command )
def server_add_task(inout_client_data, task_id, task_type):
    assert task_id not in inout_client_data

    # data = None
    # if task_type == str(Redis_Task_Type.LLM):

    # =================添加新的task的信息=================
    data = {
        'task_type': task_type,
        'task_status_key': f'Task_{task_id}_Status',
        'task_result_key': f'Task_{task_id}_Result',
        'command_system': {
            # 'obj': None,
            # 'thread': None,
            # 'cmd_id': {
            #     'cmd_status_key': None, # 'cmd_status_key': f'Task_{task_id}_Status_CMD_{cmd_id}
            #     'cmd_result_key': None, # 'cmd_result_key': f'Task_{task_id}_Result_CMD_{cmd_id}
            # },
        },
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
    # =================================================

