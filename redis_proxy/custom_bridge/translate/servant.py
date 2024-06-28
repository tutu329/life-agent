from config import dred, dgreen

from redis_proxy.custom_command.t2i.protocol import Redis_Proxy_Command_T2I
from redis_proxy.custom_command.protocol import Redis_Task_Type
from tools.llm.api_client import LLM_Client

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

def _translate_command_args_stream(input_stream_key, output_stream_key, args, s_redis_client):
    llm = LLM_Client(
        url='http://127.0.0.1:8001/v1/',
        history=False,                      # 翻译不能有history
        max_new_tokens=512,                 # 翻译参数暂考虑512 tokens
        temperature=0.7,                    # 翻译参数用较高temperature
    )

    question = '''请将【原文】翻译为英文，不要解读，直接返回翻译结果：
###原文###
{content}
'''

    dict_list = s_redis_client.pop_stream(key=input_stream_key)
    for arg_dict in dict_list:
        for arg_name in args:
            if arg_name in arg_dict :
                # 需要翻译的arg
                translated_arg = llm.ask_prepare(in_question=question.format(content=arg_name)).get_answer_and_sync_print()
                # 翻译后回写到arg_dict
                arg_dict[arg_name] = translated_arg

    for arg_dict in dict_list:
        s_redis_client.add_stream(stream_key=output_stream_key, data=arg_dict)

def translate_servant(inout_client_data, client_bridge_data, s_redis_client):
    dred(f'client_bridge_data: {client_bridge_data}')

    # 类型为input
    # command为Redis_Proxy_Command_T2I.DRAW或DRAWS
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
            _translate_command_args_stream(o_key, b_key, args, s_redis_client)

    # 类型为input或output
    # command为：如Redis_Proxy_Command_LLM.ASK
    pass