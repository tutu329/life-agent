from singleton import singleton
from dataclasses import asdict
import uuid

from redis_client import Redis_Client
from config import Global, dred, dgreen
# from redis_proxy.redis_proxy_server import Redis_Task_Type, Redis_Task_LLM_Data, LLM_Ask_Data

from redis_proxy.custom_command.protocol import Redis_Task_Type
from redis_proxy.custom_bridge.protocol import Redis_Bridge_Type
from redis_proxy.custom_bridge.protocol import Bridge_Para
from redis_proxy.custom_command.llm.protocol import Redis_Proxy_Command_LLM, LLM_Init_Para, LLM_Ask_Para
from redis_proxy.custom_command.t2i.protocol import Redis_Proxy_Command_T2I, T2I_Init_Para, T2I_Draw_Para
import random, json5


s_redis = Redis_Client(host='192.168.124.33', port=8010, invoker='redis_proxy_client')  # winu-server

# client，仅通过redis发送启动任务的消息，所有任务由Redis_Task_Server后台异步解析和处理
@singleton
class Redis_Proxy_Client():
    def __init__(self):
        self.temp_dir = Global.temp_dir

        self.client_id = 'Client_' + str(uuid.uuid4())

    # 向server发送一个消息，在server构造一个task
    def new_task(
            self,
            task_type:str,                  # task类型
    )->str:                                 # 返回task_id
        task_id = 'tid_' + str(uuid.uuid4())

        s_redis.add_stream(
            stream_key='Task_Register',
            data={
                'client_id': self.client_id,
                'task_type': str(task_type),
                'task_id': task_id,
            },
        )

        return task_id

    # 向server发送一个消息，在server构造一个bridge
    def new_bridge(
            self,
            bridge_para:Bridge_Para,
    ):
        s_redis.add_stream(
            stream_key='Bridge_Register',
            data={
                'client_id': self.client_id,
                'bridge_para_json5_string': json5.dumps(asdict(bridge_para)),
            },
        )
        dgreen(f'json5 string of bridge_para: "{json5.dumps(asdict(bridge_para))}"')
        dgreen('new_bridge() success.')

    # 对某个task下的某个command的输入或输出，进行桥接转换
    # 例如，将Draw的positive输入，翻译为英文，再传给Draw
    def add_bridge(self):
        pass

    # 向server发送一个消息，在server执行某task的一个command
    def send_command(
            self,
            task_id,        # 由new_task()返回的唯一的task_id，作为llm-obj等对象的容器id
            command:str,    # 例如：str(Redis_LLM_Command.INIT)
            args=None,      # dataclass类型，例如：redis_proxy.custom_command.llm.protocol.LLM_Ask_Para
    ):
        # 封装redis的data
        data = {
            'client_id': self.client_id,
            'task_id': task_id,
            'command': command,
        }

        if args is not None:
            arg_dict = asdict(args)
            # print(f'arg_dict: {arg_dict}')

            # redis必须将arg_dict的item加到data中，而不能嵌套dict
            for k, v in arg_dict.items():
                if v is not None:   # Para中为None的就不输入，依靠server侧的default值
                    if isinstance(v, bool):
                        # redis下，bool类型需要转换成int
                        v = int(v)
                    data[k] = v

        # 发送command
        s_redis.add_stream(
            stream_key=f'Task_{task_id}_Command',   # 与task_id一一对应的stream_key
            data=data,
        )

    # 返回task的status
    def get_status(self, task_id):
        # 返回key为'Task_xxxid_Status'（该数据由server填充）的最新数据
        key = f'Task_{task_id}_Status'
        status = s_redis.get_string(key=key)

        return status

    # 返回task的result数据
    def get_result_gen(self, task_id):       # 由new_task()返回的唯一的task_id，作为llm-obj等对象的容器id
        # 返回stream_key为'Task_xxxid_Result'（该数据由server填充）的最新数据
        stream_key = f'Task_{task_id}_Result'

        # 读取最新stream数据
        while True:
            dict_list = s_redis.pop_stream(stream_key=stream_key)
            # print('====================================================')
            for item in dict_list:

                # 打印获取的stream的dict
                # print('received dict:')
                # for k, v in item.items():
                #     if len(v)>100:
                #         print(f'\t{k}: {v[:10]}...(len: {len(v)})')
                #     else:
                #         print(f'\t{k}: {v}')

                if item['status'] != 'completed':
                    yield item['chunk']
                else:
                    # pass
                    return

    def save_image_to_file(self, image_data, file_name):
        from PIL import Image
        import io

        image = Image.open(io.BytesIO(image_data))
        image.save(f'{self.temp_dir}/{file_name}.jpg')

def main_t2i():
    t1 = Redis_Proxy_Client()

    task_id = t1.new_task(str(Redis_Task_Type.T2I))

    bridge_para = Bridge_Para()
    bridge_para.bridge_type = str(Redis_Bridge_Type.TRANSLATE)
    bridge_para.bridge_io_type = 'input'
    bridge_para.bridged_command = str(Redis_Proxy_Command_T2I.DRAW)
    bridge_para.bridged_command_args = ['positive', 'negative']
    t1.new_bridge(bridge_para=bridge_para)

    args = T2I_Init_Para(url='localhost:5100')
    t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_T2I.INIT), args=args)

    seed = random.randint(1, 1e14)
    print(f'client seed: {seed}')
    # args = T2I_Draw_Para(
    #     positive='photo of young man in an grayed blue suit, light green shirt, and yellow tie. He has a neatly styled haircut with red and silver hair and is looking directly at the camera with a neutral expression. The background is seaside. The photograph is in colored, emphasizing contrasts and shadows. The man appears to be in his late twenties or early thirties, with fair skin and short.This man looks very like young Tom Cruise.',
    #     # positive='8k raw, photo, masterpiece, super man',
    #     # negative='ugly',
    #     # seed=seed,
    #     # ckpt_name='sdxl_lightning_2step.safetensors',
    #     # height=1024,
    #     # width=1024,
    # )
    args = T2I_Draw_Para(
        positive='星际迷航中的星际战舰企业号，出现在地球外层空间',
        # positive='瑞士雪山下的小村里，好多可爱的牛在吃草',
        # positive='photo of young man in an grayed blue suit, light green shirt, and yellow tie. He has a neatly styled haircut with red and silver hair and is looking directly at the camera with a neutral expression. The background is seaside. The photograph is in colored, emphasizing contrasts and shadows. The man appears to be in his late twenties or early thirties, with fair skin and short.This man looks very like young Tom Cruise.',
        negative='',
        # negative='ugly face, bad hands, bad fingers, bad quality, poor quality, doll, disfigured, jpg, toy, bad anatomy, missing limbs, missing fingers, 3d, cgi',
    )

    # args = T2I_Draw_Para(
    #     # positive='a girl, standing on paris street, full body, long legs, cars',
    #     positive='杰作, 最佳画质, 高清, 4k, 光线追踪, 完美的脸部, 完美的眼睛, 大量的细节, 一个女孩, 胸部, 看着viewer, 性感的姿势, (cowboy shot:1.2), <lora:Tassels Dudou:0.8>,Tassels Dudou, 白色的外套, 背后的视角,',
    #     # positive='masterpiece,best quality,absurdres,highres,4k,ray tracing,perfect face,perfect eyes,intricate details,highly detailed, 1girl,(breasts:1.2),moyou,looking at viewer,sexy pose,(cowboy shot:1.2), <lora:Tassels Dudou:0.8>,Tassels Dudou,white dress,back,',
    #     negative='EasyNegativeV2,(badhandv4:1.2),bad-picture-chill-75v,BadDream,(UnrealisticDream:1.2),bad_prompt_v2,NegfeetV2,ng_deepnegative_v1_75t,ugly,(worst quality:2),(low quality:2),(normal quality:2),lowres,watermark,',
    #     template_json_file = 'api-sexy.json',
    #     seed = random.randint(1, 1e14),
    #     # ckpt_name = 'awportrait_v13.safetensors',
    #     ckpt_name = 'meichidarkMix_meichidarkV5.safetensors',
    #     height = 768,
    #     width = 512,
    #     sampler_name = 'dpmpp_2m_sde',
    #     scheduler = 'karras',
    #     steps = 72,
    #     cfg = 7,
    #     denoise = 1,
    #     batch_size = 1,
    #
    #     lora_count=1,
    #     lora1 = 'sexy-cloth-Tassels-Dudou.safetensors',
    #     lora1_wt = 0.85,
    #     lora2 = None,
    #     lora2_wt = None,
    #     lora3 = None,
    #     lora3_wt = None,
    #     lora4 = None,
    #     lora4_wt = None,
    # )
    # print(f'args: {args}')
    t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_T2I.DRAW), args=args)
    # t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_T2I.DRAWS), args=args)

    i=0
    for image_data in t1.get_result_gen(task_id):
        i += 1
        t1.save_image_to_file(image_data, file_name=f'output_{task_id}_{i}')

def main_llm():
    # c = Redis_Task_Client()
    # c.add_llm_task('2+2=')

    t1 = Redis_Proxy_Client()
    task_id = t1.new_task(str(Redis_Task_Type.LLM))

    args = LLM_Init_Para(url='http://192.168.124.33:8001/v1', max_new_tokens=1024)
    t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_LLM.INIT), args=args)
    # t1.send_command(task_id=task_id, custom_command=str(Redis_Proxy_Command_LLM.INIT), url='http://192.168.124.33:8001/v1', max_new_tokens=1024)

    args = LLM_Ask_Para(question='你是谁？我叫土土', temperature=0.6, system_prompt='你扮演甄嬛', role_prompt='你扮演洪七公')
    t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_LLM.ASK), args=args)
    # t1.send_command(task_id=task_id, custom_command=str(Redis_Proxy_Command_LLM.ASK), question='你是谁？我叫土土', temperature=0.6, system_prompt='你扮演甄嬛', role_prompt='你扮演洪七公')
    # print(f'result is:')
    for chunk in t1.get_result_gen(task_id):
        print(chunk, end='', flush=True)
    print()

if __name__ == "__main__":
    # main_llm()
    main_t2i()