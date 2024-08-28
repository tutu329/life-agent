import time
import config
from enum import Enum, unique
from typing import List, Any
from dataclasses import dataclass, asdict, field

from config import dred, dgreen

from redis_proxy.custom_command.llm.protocol import Redis_Proxy_Command_LLM
from redis_proxy.custom_command.t2i.protocol import Redis_Proxy_Command_T2I

from redis_client import Redis_Client
from redis_proxy.thread import Task_Worker_Thread
from utils.task import Status

from redis_proxy.custom_bridge.translate.servant import translate_servant


@unique
class Redis_Bridge_Type(Enum):
    TRANSLATE = 'TRANSLATE'

# bridge参数：桥接输入还是输出、桥接的具体cmd和args
@dataclass
class Bridge_Para():
    bridge_type:Any = None              # 如: Redis_Bridge_Type.TRANSLATE
    bridge_io_type:str = None           # 如: 'input'或'output'


    # input或output
    bridged_command:Any = None          # 如: Redis_Proxy_Command_T2I.DRAW
    # input
    bridged_command_args:Any = None     # 如: ['positive', 'negative']

# 由于某一类command对应n个bridge，因此bridge不是某个task或者某个task下的某个command的一部分
# 因此bridge_system是client的一部分，而不是task的一部分
def server_add_and_start_bridge_servant(inout_client_data, s_redis_client, bridge_para:Bridge_Para):
    dgreen(f'inout_client_data: {inout_client_data}')
    dgreen(f'bridge_para: {bridge_para}')
    # client的输入
    bridge_type = bridge_para['bridge_type']
    bridge_io_type = bridge_para['bridge_io_type']
    bridged_command = bridge_para['bridged_command']
    if 'bridged_command_args' in bridge_para:
        bridged_command_args = bridge_para['bridged_command_args']
    else:
        bridged_command_args = None

    # 读取bridge_system
    if 'bridge_system' in inout_client_data:
        client_bridge_system = inout_client_data['bridge_system']
    else:
        inout_client_data['bridge_system'] = []
        client_bridge_system = inout_client_data['bridge_system']

    # 读取client现有bridge数量
    # client_bridge_num = len(client_bridge_system)
    # client_bridge_num += 1

    # bridge的参数和线程对象
    client_bridge_data = {
        # 'obj': None,  # 如llm进行translate，并不需要历史状态，因此暂不需要存放llm的obj状态
        'thread': Task_Worker_Thread(),

        # key的桥接（bridge的核心任务：将原有task中的redis key转为桥接后的key）
        # 核心流程是：具体某个command执行时，其输入输出的key将被bridge到新的key中（且command流程不需自知）

        # bridge类型
        'bridge_type':bridge_type,
        'bridge_io_type':bridge_io_type,

        # input或output类型
        'bridged_command':bridged_command,
        # input类型
        'bridged_command_args':bridged_command_args,
        # input类型：修改redis_proxy_server侧的command stream key：
        'bridged_command_stream_key' :   'Task_{task_id}_Command_Bridged',  # 原为'Task_{task_id}_Command'

        # output类型：在s_redis_proxy_server_data中、server_add_task()中，修改所有task的输出key：
        'bridged_task_status_key' :      'Task_{task_id}_Status_Bridged',   # 原为'Task_{task_id}_Status'
        'bridged_task_result_key' :      'Task_{task_id}_Result_Bridged',   # 原为'Task_{task_id}_Result'
    }
    dgreen('==================================================================')
    dgreen(f'client_bridge_data: {client_bridge_data}')
    dgreen('==================================================================')


    # bridge的轮询任务(只对原stream和桥接后stream进行转换，从而确保异步)
    def bridge_polling_callback(out_task_info_must_be_here):
        # 注意：这里必须是一个独立的Redis_Client，否则会和redis_proxy_server下的s_redis_client冲突
        bridge_redis_client = Redis_Client(host='192.168.124.33', port=8010, invoker='bridge_polling_callback')
        # print('@@@@@@@@@@@@@@@@@@@@@@@@@@bridge_polling_callback() invoke Redis_Client()@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')

        while True:
            if out_task_info_must_be_here['status'] == Status.Cancelling:
                break

            if bridge_type==str(Redis_Bridge_Type.TRANSLATE):
                translate_servant(inout_client_data, client_bridge_data, bridge_redis_client)

            time.sleep(config.Global.redis_proxy_server_sleep_time)

    # 启动bridge的thread
    thread = client_bridge_data['thread']
    thread.init(in_callback_func=bridge_polling_callback)
    thread.start()

    # 写入bridge_data
    client_bridge_system.append(client_bridge_data)

