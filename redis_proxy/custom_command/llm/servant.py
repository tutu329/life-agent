import pprint

from config import dred, dblue, dgreen
import config

from redis_proxy.custom_command.llm.protocol import Redis_Proxy_Command_LLM
from tools.llm.api_client import LLM_Client
from redis_proxy.thread import Task_Worker_Thread

from redis_proxy.custom_command.llm.protocol import Config

def call_llm_servant(
        command,
        task_obj_already_exists,
        output_callback,    # output_callback(output_string:str, use_byte:bool)
        finished_callback,  # finished_callback()
        **command_data_dict
):  # 返回new_task_obj
    if command == str(Redis_Proxy_Command_LLM.INIT):
        new_task_obj = LLM_Client(**command_data_dict)
        return new_task_obj

    if command == str(Redis_Proxy_Command_LLM.ASK):
        gen = task_obj_already_exists.ask_prepare(**command_data_dict).get_answer_generator()
        for chunk in gen:
            output_callback(output_string=chunk, use_byte=False)
        finished_callback()

        return task_obj_already_exists

def llm_servant(s_redis_proxy_server_data, s_redis_client, status_key, result_key, task_id, client_id, command, command_id,  **arg_dict):
    # dgreen(f'command from client: {arg_dict}')
    cid = client_id
    tid = task_id
    command = command
    cmd_id = command_id
    cmd_data = s_redis_proxy_server_data.clients[cid].tasks[tid].commands
    # cmd_data = s_redis_proxy_server_data[cid][tid]['command_system']

    # 公有参数
    if 'max_new_tokens' in arg_dict:
        max_new_tokens = arg_dict['max_new_tokens']
    else:
        max_new_tokens = config.Global.llm_max_new_tokens

    if 'temperature' in arg_dict:
        temperature = arg_dict['temperature']
    else:
        temperature = config.Global.llm_temperature

    # INIT
    if command==str(Redis_Proxy_Command_LLM.INIT):
        # 初始化 LLM_Client
        if 'url' in arg_dict:
            url = arg_dict['url']
        else:
            url = config.Domain.llm_url

        if 'history' in arg_dict:
            history = arg_dict['history']
        else:
            history = True

        dred(f'----------history: {history}--------------')
        cmd_data['obj'] = LLM_Client(
            url=url,
            history=history,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )
        cmd_data['responsing_cmds_info'] = {}


        dred(f'----------cmd_data->obj: {cmd_data["obj"]}--------------')
        pprint.pprint(s_redis_proxy_server_data)


        # 初始化 Task_Worker_Thread
        # task_data['command_system'][0]['thread'] = Task_Worker_Thread()

    # ASK
    if command==str(Redis_Proxy_Command_LLM.ASK):
        def llm_callback(out_task_info_must_be_here, status_key, result_key, llm_obj, arg_dict):
            # dred(f'llm_callback() invoked: stats({out_task_info_must_be_here}), question({question})')
            status = out_task_info_must_be_here

            # system_prompt
            if 'system_prompt' in arg_dict:
                # print(f"system_prompt is : {arg_dict['system_prompt']}")
                llm_obj.set_system_prompt(arg_dict['system_prompt'])

            # role_prompt
            if 'role_prompt' in arg_dict:
                # print(f"role_prompt is : {arg_dict['role_prompt']}")
                llm_obj.set_role_prompt(arg_dict['role_prompt'])

            # question
            question = arg_dict['question']

            # temperature
            if 'temperature' in arg_dict:
                temperature = arg_dict['temperature']
                # dred(f'------------servant-llm_callback(): ask_prepare() started.------------')
                # dred(f'----------history2: {llm_obj.history}--------------')
                gen = llm_obj.ask_prepare(question=question, temperature=temperature).get_answer_generator()
            else:
                # dred(f'------------servant-llm_callback(): ask_prepare() started.------------')
                gen = llm_obj.ask_prepare(question=question).get_answer_generator()

            # 设置responsing_cmds_info
            cmd_data['responsing_cmds_info'][cmd_id] = 'running'
            s_redis_client.add_stream(stream_key=f'responsing_cmds_info_{tid}', data=cmd_data['responsing_cmds_info'])

            # llm返回数据给redis的stream
            for chunk in gen:
                # print(chunk, end='', flush=True)
                data = {
                    'chunk_data_type': 'text',
                    'chunk': chunk,
                    'chunk_use_byte': int(False),
                    'status': 'running',
                }
                s_redis_client.add_stream(stream_key=result_key, data=data)
                s_redis_client.set_string(key=status_key,value_string='running')

            # 结束的状态返回给redis
            data = {
                'status': 'completed',
            }
            s_redis_client.add_stream(stream_key=result_key, data=data)
            s_redis_client.set_string(key=status_key,value_string='completed')

            # 设置responsing_cmds_info
            cmd_data['responsing_cmds_info'][cmd_id] = 'completed'
            s_redis_client.add_stream(stream_key=f'responsing_cmds_info_{tid}', data=cmd_data['responsing_cmds_info'])

        # ***************每一个command需要新增一个thread，但后续必须核实command_id的问题*****************
        cmd_data['thread'] = Task_Worker_Thread()
        # ***************每一个command需要新增一个thread，但后续必须核实command_id的问题*****************

        llm = cmd_data['obj']


        dred(f'----------cmd_data->obj: {cmd_data["obj"]}--------------')
        pprint.pprint(s_redis_proxy_server_data)


        # print(f'llm: {llm}')
        thread = cmd_data['thread']
        thread.init(in_callback_func=llm_callback, status_key=status_key, result_key=result_key, llm_obj=llm, arg_dict=arg_dict)
        thread.start()

        if not Config.command_parallel:
            thread.join()   # 等待线程完成

    if command==str(Redis_Proxy_Command_LLM.CANCEL):
        llm = cmd_data['obj']
        if llm is not None:
            llm.cancel_response()
