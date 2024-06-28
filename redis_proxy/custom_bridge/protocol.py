def server_invoking_bridge():
    pass

def server_add_bridge(inout_client_data, bridge_type):
    # 由于某一类command对应n个bridge，因此bridge不是某个task或者某个task下的某个command的一部分
    # 因此bridge_system是client的一部分
    bridge_data = {
        'bridge_type':bridge_type,
        'obj': None,
        'thread': None,
    }

    # 读取bridge_system
    if 'bridge_system' in inout_client_data:
        bridge_system = inout_client_data['bridge_system']
    else:
        inout_client_data['bridge_system'] = {}
        bridge_system = inout_client_data['bridge_system']
    # 写入bridge_data
    bridge_system['bridge_type'] = bridge_data
