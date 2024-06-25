
from config import dred, dgreen
import config

from redis_proxy.custom_command.t2i.protocol import Redis_Proxy_Command_T2I
from tools.t2i.api_client_comfy import Comfy, Work_Flow_Type
from redis_proxy.thread import Task_Worker_Thread

def _get_arg(arg_str, default, **arg_dict):
    arg = default
    if arg_str in arg_dict:
        arg = arg_dict[arg_str]
    return arg

def t2i_servant(s_redis_proxy_server_data, s_redis_client, **arg_dict):
        # dgreen(f'command from client: {arg_dict}')
        cid = arg_dict['client_id']
        tid = arg_dict['task_id']
        command = arg_dict['command']
        task_data = s_redis_proxy_server_data[cid][tid]

        # 公有参数
        # if 'max_new_tokens' in arg_dict:
        #     max_new_tokens = arg_dict['max_new_tokens']
        # else:
        #     max_new_tokens = config.Global.llm_max_new_tokens


        # INIT
        if command==str(Redis_Proxy_Command_T2I.INIT):
            # 初始化 LLM_Client
            if 'url' in arg_dict:
                url = arg_dict['url']
            else:
                url = config.Global.llm_url

            # 注册obj
            task_data['task_system'][0]['obj'] = Comfy()

            # 注册Task_Worker_Thread
            # 而T2I，由于seed可能需要改变，不同的command对应不同的thread，这里不需要new一个thread
            # task_data['task_system'][0]['thread'] = None
            task_data['task_system'][0]['thread'] = Task_Worker_Thread()

        # ASK
        if command==str(Redis_Proxy_Command_T2I.DRAW):
            def callback(out_task_info_must_be_here, status_key, result_key, obj, arg_dict):
                # dred(f'llm_callback() invoked: stats({out_task_info_must_be_here}), question({question})')
                status = out_task_info_must_be_here

                # t2i参数获取
                positive = _get_arg(arg_str='positive', default='', **arg_dict)
                negative = _get_arg(arg_str='negative', default='', **arg_dict)
                ckpt_name = _get_arg(arg_str='ckpt_name', default='sdxl_lightning_2step.safetensors', **arg_dict)
                height = _get_arg(arg_str='height', default=1024, **arg_dict)
                width = _get_arg(arg_str='width', default=1024, **arg_dict)

                # t2i返回数据给redis的stream
                obj.set_workflow_type(Work_Flow_Type.simple)
                obj.set_simple_work_flow(
                    positive=positive,
                    negative=negative,
                    ckpt_name=ckpt_name,
                    height=height,
                    width=width,
                )

                # t2i运行的状态返回给redis
                s_redis_client.set_string(key=status_key,value_string='running')

                # t2i运行
                images = obj.get_images()

                # t2i的images返回给redis
                for node_id in images:
                    for image_data in images[node_id]:
                        data = {
                            'chunk_data_type':'image_data',
                            'chunk': image_data,
                            'chunk_use_byte': int(True),
                            'status': 'completed',
                        }
                        s_redis_client.add_stream(stream_key=result_key, data=data)

                # t2i的images返回完毕
                data = {
                    'status': 'completed',
                }
                s_redis_client.add_stream(stream_key=result_key, data=data)
                s_redis_client.set_string(key=status_key,value_string='completed')

            # t2i流程启动
            obj = task_data['task_system'][0]['obj']

            status_key = task_data['task_status_key']
            result_key = task_data['task_result_key']

            # 与LLM调用不同，LLM的后续ask需要依赖之前的ask的结果，因此LLM同一个task，不同的command对应同一个thread
            # 而T2I，由于seed可能需要改变，不同的command对应不同的thread
            # task_data['task_system'][0]['thread'] = Task_Worker_Thread()
            thread = task_data['task_system'][0]['thread']
            thread.init(in_callback_func=callback, status_key=status_key, result_key=result_key, obj=obj, arg_dict=arg_dict)
            thread.start()

        # if command==str(Redis_Proxy_Command_LLM.CANCEL):
        #     llm = task_data['task_system'][0]['obj']
        #     if llm is not None:
        #         llm.cancel_response()
