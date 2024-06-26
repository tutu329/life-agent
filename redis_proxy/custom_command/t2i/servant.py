
from config import dred, dgreen
import config

from redis_proxy.custom_command.t2i.protocol import Redis_Proxy_Command_T2I
from tools.t2i.api_client_comfy import Comfy, Work_Flow_Type
from redis_proxy.thread import Task_Worker_Thread

import random

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
            task_data['task_system'][0]['thread'] = None
            # task_data['task_system'][0]['thread'] = Task_Worker_Thread()

        # DRAW
        if command==str(Redis_Proxy_Command_T2I.DRAW) or command==str(Redis_Proxy_Command_T2I.DRAWS):
            def callback(out_task_info_must_be_here, status_key, result_key, obj, arg_dict):
                dred(f't2i_callback() invoked:')
                for k, v in arg_dict.items():
                    dgreen(f'\t {k}: {v}')

                status = out_task_info_must_be_here

                # t2i参数获取
                if command==str(Redis_Proxy_Command_T2I.DRAW):
                    print(f'------------------command: {command}------------------')
                    positive = _get_arg(arg_str='positive', default='photo of young man in an grayed blue suit, light green shirt, and yellow tie. He has a neatly styled haircut with red and silver hair and is looking directly at the camera with a neutral expression. The background is seaside. The photograph is in colored, emphasizing contrasts and shadows. The man appears to be in his late twenties or early thirties, with fair skin and short.This man looks very like young Tom Cruise.', **arg_dict)
                    negative = _get_arg(arg_str='negative', default='ugly face, bad hands, bad fingers, bad quality, poor quality, doll, disfigured, jpg, toy, bad anatomy, missing limbs, missing fingers, 3d, cgi', **arg_dict)
                    template_json_file = _get_arg(arg_str='template_json_file', default='api-sd3-tom.json', **arg_dict)
                    seed = _get_arg(arg_str='seed', default=random.randint(1, 1e14), **arg_dict)
                    ckpt_name = _get_arg(arg_str='ckpt_name', default='sd3_medium.safetensors', **arg_dict)
                    height = _get_arg(arg_str='height', default=1024, **arg_dict)
                    width = _get_arg(arg_str='width', default=1024, **arg_dict)
                    sampler_name = _get_arg(arg_str='sampler_name', default='dpmpp_2m', **arg_dict)
                    scheduler = _get_arg(arg_str='scheduler', default='sgm_uniform', **arg_dict)
                    steps = _get_arg(arg_str='steps', default=30, **arg_dict)
                    cfg = _get_arg(arg_str='cfg', default=4.5, **arg_dict)
                    denoise = _get_arg(arg_str='denoise', default=1, **arg_dict)
                    batch_size = _get_arg(arg_str='batch_size', default=1, **arg_dict)

                    # t2i返回数据给redis的stream
                    obj.set_sd3_workflow(
                        positive=positive,
                        negative=negative,
                        template_json_file=template_json_file,
                        seed=seed,
                        ckpt_name=ckpt_name,
                        height=height,
                        width=width,
                        sampler_name=sampler_name,
                        scheduler=scheduler,
                        steps=steps,
                        cfg=cfg,
                        denoise=denoise,
                        batch_size=batch_size,
                    )
                elif command==str(Redis_Proxy_Command_T2I.DRAWS):
                    print(f'------------------command: {command}------------------')
                    positive = _get_arg(arg_str='positive', default='masterpiece,best quality,absurdres,highres,4k,ray tracing,perfect face,perfect eyes,intricate details,highly detailed, 1girl,(breasts:1.2),moyou,looking at viewer,sexy pose,(cowboy shot:1.2), <lora:Tassels Dudou:0.8>,Tassels Dudou,white dress,back,', **arg_dict)
                    negative = _get_arg(arg_str='negative', default='EasyNegativeV2,(badhandv4:1.2),bad-picture-chill-75v,BadDream,(UnrealisticDream:1.2),bad_prompt_v2,NegfeetV2,ng_deepnegative_v1_75t,ugly,(worst quality:2),(low quality:2),(normal quality:2),lowres,watermark,', **arg_dict)
                    template_json_file = _get_arg(arg_str='template_json_file', default='api-sexy.json', **arg_dict)
                    seed = _get_arg(arg_str='seed', default=random.randint(1, 1e14), **arg_dict)
                    ckpt_name = _get_arg(arg_str='ckpt_name', default='meichidarkMix_meichidarkV5.safetensors', **arg_dict)
                    height = _get_arg(arg_str='height', default=768, **arg_dict)
                    width = _get_arg(arg_str='width', default=512, **arg_dict)
                    sampler_name = _get_arg(arg_str='sampler_name', default='dpmpp_2m_sde', **arg_dict)
                    scheduler = _get_arg(arg_str='scheduler', default='karras', **arg_dict)
                    steps = _get_arg(arg_str='steps', default=20, **arg_dict)
                    cfg = _get_arg(arg_str='cfg', default=7, **arg_dict)
                    denoise = _get_arg(arg_str='denoise', default=1, **arg_dict)
                    batch_size = _get_arg(arg_str='batch_size', default=1, **arg_dict)

                    lora1 = _get_arg(arg_str='lora1', default='sexy-cloth-Tassels-Dudou.safetensors', **arg_dict)
                    lora1_wt = _get_arg(arg_str='lora1_wt', default=0.85, **arg_dict)
                    lora2 = _get_arg(arg_str='lora2', default='None', **arg_dict)
                    lora2_wt = _get_arg(arg_str='lora2_wt', default=1, **arg_dict)
                    lora3 = _get_arg(arg_str='lora3', default='None', **arg_dict)
                    lora3_wt = _get_arg(arg_str='lora3_wt', default=1, **arg_dict)
                    lora4 = _get_arg(arg_str='lora4', default='None', **arg_dict)
                    lora4_wt = _get_arg(arg_str='lora4_wt', default=1, **arg_dict)


                    # t2i返回数据给redis的stream
                    obj.set_sexy_workflow(
                        positive=positive,
                        negative=negative,
                        template_json_file=template_json_file,
                        seed=seed,
                        ckpt_name=ckpt_name,
                        height=height,
                        width=width,
                        sampler_name=sampler_name,
                        scheduler=scheduler,
                        steps=steps,
                        cfg=cfg,
                        denoise=denoise,
                        batch_size=batch_size,
                        lora1=lora1,
                        lora1_wt=lora1_wt,
                        lora2=lora2,
                        lora2_wt=lora2_wt,
                        lora3=lora3,
                        lora3_wt=lora3_wt,
                        lora4=lora4,
                        lora4_wt=lora4_wt,
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
                            'chunk_use_byte': int(True),    # chunk_use_byte==True, 则chunk数据不能被转换为utf-8 string
                            'status': 'running',
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
            task_data['task_system'][0]['thread'] = Task_Worker_Thread()
            thread = task_data['task_system'][0]['thread']
            thread.init(in_callback_func=callback, status_key=status_key, result_key=result_key, obj=obj, arg_dict=arg_dict)
            thread.start()

        # if command==str(Redis_Proxy_Command_LLM.CANCEL):
        #     llm = task_data['task_system'][0]['obj']
        #     if llm is not None:
        #         llm.cancel_response()
