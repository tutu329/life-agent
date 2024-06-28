from enum import Enum, unique

from config import dred, dgreen

@unique
class Redis_Bridge_Type(Enum):
    TRANSLATE = 'TRANSLATE'

def server_invoking_bridge():
    pass

def server_add_bridge(inout_client_data, bridge_type:str):
    # 读取bridge_system
    if 'bridge_system' in inout_client_data:
        client_bridge_system = inout_client_data['bridge_system']
    else:
        inout_client_data['bridge_system'] = {}
        client_bridge_system = inout_client_data['bridge_system']

    # 读取client现有bridge数量
    client_bridge_num = len(client_bridge_system)
    client_bridge_num += 1

    # 由于某一类command对应n个bridge，因此bridge不是某个task或者某个task下的某个command的一部分
    # 因此bridge_system是client的一部分
    client_bridge_data = {
        'bridge_type':bridge_type,
        'obj': None,
        'thread': None,

        # key的桥接（bridge的核心任务：将原有task中的redis key转为桥接后的key）
        # 核心流程是：具体某个command执行时，其输入输出的key将被bridge到新的key中（且command流程不需自知）
        # 1）修改redis_proxy_server侧的command stream key：
        'bridged_command_stream_key' :   'Task_{task_id}_Command_Bridged',
        # 2）在s_redis_proxy_server_data中、server_add_task()中，修改所有task的输出key：
        'bridged_task_status_key' :      'Task_{task_id}_Status_Bridged',
        'bridged_task_result_key' :      'Task_{task_id}_Result_Bridged',
    }

    # 创建并启动bridge的轮询任务
    # bridge_data['obj'] =
    # bridge_data['thread'] =

    # bridge的轮询任务
    def bridge_polling():
        pass

    # 启动bridge的thread


    # 写入bridge_data
    client_bridge_system['bridge_type'] = client_bridge_data

