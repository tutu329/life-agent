def server_invoking_bridge():
    pass

def server_add_bridge(inout_client_data, bridge_type):
    # 由于某一类command对应n个bridge，因此bridge不是某个task或者某个task下的某个command的一部分
    # 因此bridge_system是client的一部分
    bridge_data = {
        'bridge_type':bridge_type,
        'obj': None,
        'thread': None,

        # key的桥接（bridge的核心任务：将原有task中的redis key转为桥接后的key）
        # 核心流程是：具体某个command执行时，其输入输出的key将被bridge到新的key中（且command流程不需自知）
        'task_status_bridged_key': None,    # f'Task_{task_id}_Status',
        'task_result_bridged_key': None,    # f'Task_{task_id}_Result',
    }

    # 创建并启动bridge的轮询任务
    # bridge_data['obj'] =
    # bridge_data['thread'] =

    # bridge的轮询任务
    def bridge_polling():
        pass

    # 启动bridge的thread

    # 读取bridge_system
    if 'bridge_system' in inout_client_data:
        bridge_system = inout_client_data['bridge_system']
    else:
        inout_client_data['bridge_system'] = {}
        bridge_system = inout_client_data['bridge_system']
    # 写入bridge_data
    bridge_system['bridge_type'] = bridge_data

