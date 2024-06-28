from config import dred, dgreen

from redis_proxy.custom_command.t2i.protocol import Redis_Proxy_Command_T2I
from redis_proxy.custom_command.protocol import Redis_Task_Type

# 获取所有符合要求的task_ids
def get_task_ids_for_command(inout_client_data, cmd:str):
    task_ids = []
    for k, v in inout_client_data.items():
        if 'task_type' in v:
            task_id = k
            task_dict = v
            if task_dict['task_type']==cmd: # 如 str(Redis_Task_Type.T2I)
                task_ids.append(task_id)
    return task_ids

def _translate_command_args_stream(input_stream_key, output_stream_key, args):
    pass

def translate_servant(inout_client_data, client_bridge_data):
    dred(f'client_bridge_data: {client_bridge_data}')

    # 类型为input
    # command为Redis_Proxy_Command_T2I.ASK或ASKS
    if client_bridge_data['bridge_io_type']=='input' and (client_bridge_data['bridged_command']==str(Redis_Proxy_Command_T2I.DRAW) or client_bridge_data['bridged_command']==str(Redis_Proxy_Command_T2I.DRAWS) ):
        original_cmd_key = 'Task_{task_id}_Command'                         # 'Task_{task_id}_Command'
        bridged_cmd_key = client_bridge_data['bridged_command_stream_key']  # 'Task_{task_id}_Command_Bridged'

        # 对本client_id下的所有task进行检查，如果有符合条件的task_id_i及command, 进行translate操作，生成新的command stream
        task_ids = get_task_ids_for_command(inout_client_data, str(Redis_Task_Type.T2I))
        for task_id in task_ids:
            dred(f'translate_servant开始处理任务: task_id({task_id})')
            o_key = original_cmd_key.format(task_id=task_id)
            b_key = bridged_cmd_key.format(task_id=task_id)

            # 将以下信息注入，表明这些task需要桥接command stream
            inout_client_data[task_id]['task_command_key_bridged'] = b_key

            # 对command stream下所有记录的需桥接args，进行翻译，并生成bridge后的command stream
            args = client_bridge_data['bridged_command_args']
            _translate_command_args_stream(o_key, b_key, args)

    pass