import config
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


s_redis = Redis_Client(host=config.Domain.redis_server_domain, port=config.Port.redis_client, invoker='redis_proxy_client')  # win-server

# client，仅通过redis发送启动任务的消息，所有任务由Redis_Task_Server后台异步解析和处理
@singleton
class Redis_Proxy_Client():
    def __init__(self):
        self.temp_dir = Global.temp_dir

        self.client_id = 'Client_' + str(uuid.uuid4())

        self.task_id = None

    # 向server发送一个消息，在server构造一个task
    def new_task(
            self,
            task_type,  # task类型：如Redis_Task_Type.T2I
    ):
        task_id = 'tid_' + str(uuid.uuid4())

        s_redis.add_stream(
            stream_key='Task_Register',
            data={
                'client_id': self.client_id,
                'task_type': str(task_type),
                'task_id': task_id,
            },
        )

        self.task_id = task_id
        return self

    # 向server发送一个消息，在server构造一个bridge。 对某个task下的某个command的输入或输出，进行桥接转换。
    # 例如，将Draw的输入positive和negtive，翻译为英文，再传给Draw
    def new_bridge(
            self,
            bridge_para:Bridge_Para,
    ):
        bridge_para = asdict(bridge_para)
        para = {}
        # 对一些参数进行str转换
        for k,v in bridge_para.items():
            if k=='bridge_type' or k=='bridged_command':
                para[k]=str(v)
            else:
                para[k] = v
        para = json5.dumps(para)

        s_redis.add_stream(
            stream_key='Bridge_Register',
            data={
                'client_id': self.client_id,
                'bridge_para_json5_string': para,
            },
        )
        dgreen(f'new_bridge() success: "{para}"')

    # 向server发送一个消息，在server执行某task的一个command
    def send_command(
            self,
            # task_id,        # 由new_task()返回的唯一的task_id，作为llm-obj等对象的容器id
            command,        # 例如：Redis_LLM_Command.INIT
            args=None,      # dataclass类型，例如：redis_proxy.custom_command.llm.protocol.LLM_Ask_Para
    ):
        task_id = self.task_id
        # 封装redis的data
        data = {
            'client_id': self.client_id,
            'task_id': task_id,
            'command': str(command),    # 例如：str(Redis_LLM_Command.INIT)
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

        return self

    # 返回task的status
    def get_status(self, task_id):
        # 返回key为'Task_xxxid_Status'（该数据由server填充）的最新数据
        key = f'Task_{task_id}_Status'
        status = s_redis.get_string(key=key)

        return status

    def print_stream(self):
        for chunk in self.get_result_gen():
            print(chunk, end='', flush=True)
        print()

    # 返回task的result数据
    def get_result_gen(self):       # 由new_task()返回的唯一的task_id，作为llm-obj等对象的容器id
        task_id = self.task_id

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
    task_id = t1.new_task(Redis_Task_Type.T2I)

    bridge_para = Bridge_Para()
    bridge_para.bridge_type = Redis_Bridge_Type.TRANSLATE
    bridge_para.bridge_io_type = 'input'
    bridge_para.bridged_command = Redis_Proxy_Command_T2I.DRAW
    bridge_para.bridged_command_args = ['positive', 'negative']     # 对所有args进行如translate的操作
    # t1.new_bridge(bridge_para=bridge_para)

    args = T2I_Init_Para(url='localhost:5100')
    t1.send_command(command=Redis_Proxy_Command_T2I.INIT, args=args)

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

    # args = T2I_Draw_Para(
    #     # positive='星际迷航中的星际战舰企业号，出现在地球外层空间',
    #     positive='瑞士雪山下的小村里，好多可爱的牛在吃草',
    #     # positive='photo of young man in an grayed blue suit, light green shirt, and yellow tie. He has a neatly styled haircut with red and silver hair and is looking directly at the camera with a neutral expression. The background is seaside. The photograph is in colored, emphasizing contrasts and shadows. The man appears to be in his late twenties or early thirties, with fair skin and short.This man looks very like young Tom Cruise.',
    #     negative='',
    #     # negative='ugly face, bad hands, bad fingers, bad quality, poor quality, doll, disfigured, jpg, toy, bad anatomy, missing limbs, missing fingers, 3d, cgi',
    # )

    args = T2I_Draw_Para(
        # positive='a girl, standing on paris street, full body, long legs, cars',
        # positive='杰作, 最佳画质, 高清, 4k, 光线追踪, 完美的脸部, 完美的眼睛, 大量的细节, 一个女孩, 胸部, 看着viewer, 性感的姿势, (cowboy shot:1.2), <lora:Tassels Dudou:0.8>,Tassels Dudou, 白色的外套, 背后的视角,',
        # positive='masterpiece,best quality,absurdres,highres,4k,ray tracing,perfect face,perfect eyes,intricate details,highly detailed, 1girl,(breasts:1.2),moyou,looking at viewer,sexy pose,(cowboy shot:1.2), <lora:Tassels Dudou:0.8>,Tassels Dudou,white dress,back,',
        # negative='EasyNegativeV2,(badhandv4:1.2),bad-picture-chill-75v,BadDream,(UnrealisticDream:1.2),bad_prompt_v2,NegfeetV2,ng_deepnegative_v1_75t,ugly,(worst quality:2),(low quality:2),(normal quality:2),lowres,watermark,',
        positive= "Ultra-realistic 8k CG,masterpiece,best quality,(photorealistic:1.4),(EOS R8,50mm,F1.2,8K,RAW photo:1.2),HDR,absurdres,Professional,RAW photo,(film grain:1.1),Bokeh,(EOS R8,50mm,F1.2,8K,RAW photo:1.2),((Depth of field)),EF 70mm,raytracing,detailed shadows,dim light,POV, ((wallpaper 8k)), ((high detailed)), ((masterpiece)), ((best quality:1.2)), ((hdr)), ((absurdres)), ((RAW photo)), ( depth of field),(sunny city background ),(highlight face detail), blush, (realistic:1.3), (realistic shadow), sweaty body, beautiful eyes, big eyes, detailed eyes, looking at viewers, smile, ((panties pulled aside fuck)), <lora:panties_pulled_aside_fuck.v1.0:1>, mature woman, realistic style, (wearing erotic pantie:1.3), (wearing open shirt:1.3), (breasts out:1.3), topless, (insertion,vaginal), nude, (black lace lingerie nightgown:1.3), beautiful legs, thin legs, 1girl, blonde hair, having sex, bangs, 1man, penis, pussy, embarrassed facial expression, enlighted ,big penis, Pussy, Pussy Juice, cumshot, cumdrip, semen , anus, cum-covered, volumetric shadows, indoors, Cum In Pussy, Hetero, Overflow, (Penetration:1.5), sweat, vaginal penetration, veins, high res, ultra-realistic 8k, perfect artwork, ((perfect female figure)), narrow waist, lens flare, soft lighting, best quality cloth,full body, beautiful, perfect face, perfect body,canon50",
        negative= "easynegative,ng_deepnegative_v1_75t, badhandv4,(worst quality:2),(low quality:2),(normal quality:2),lowres,bad anatomy,bad hands,normal quality,((monochrome)),((grayscale)),((watermark)), uneven eyes, ugly eyesbad_prompt_version2-neg,verybadimagenegative_v1.3, (worst quality:2),(low quality:2),(normal quality:1.6),monochrome,(watermark:1.3),artist name,character name,text,bad anatomy,sketch,duplicate,(ng_deepnegative_v1_75t),(negative_hand-neg:1.2),bad_pictures,EasyNegative,FastNegativeV2, illustration, 3d, sepia, painting, cartoons, sketch, easynegative,ng_deepnegative_v1_75t, badhandv4,(worst quality:2),(low quality:2),(normal quality:2),lowres,bad anatomy,bad hands,normal quality,((monochrome)),((grayscale)),((watermark)), uneven eyes, ugly eyesbad_prompt_version2-neg,verybadimagenegative_v1.3, (worst quality:2),(low quality:2),(normal quality:1.6),monochrome,(watermark:1.3),artist name,character name,text,bad anatomy,sketch,duplicate,(ng_deepnegative_v1_75t),(negative_hand-neg:1.2),bad_pictures,EasyNegative,FastNegativeV2, bad anatomy, bad res, bad quality, error, malformed, art by bad-artist, bad-image-v2-39000, bad-hands-5, art by negprompt5, lowres, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, artist name, (worst quality, low quality, extra digits, loli, loli face:1.3), 3 arms, 3 hands, (((bad hands))), ((2heads)), pants, panties, cartoon, 3d, ((disfigured)), ((bad art)), ((deformed)),((extra limbs)),((close up)),((b&w)), wierd colors, blurry, (((duplicate))), ((morbid)), ((mutilated)), [out of frame], extra fingers, mutated hands, ((poorly drawn hands)), ((poorly drawn face)), (((mutation))), (((deformed))), ((ugly)), blurry, ((bad anatomy)), (((bad proportions))), ((extra limbs)), (((disfigured))), out of frame, ugly, extra limbs, (bad anatomy), gross proportions, (malformed limbs), ((missing arms)), ((missing legs)), (((extra arms))), (((extra legs))), mutated hands, (fused fingers), (too many fingers), ((worst eyes)), ((uneven eyes)), (anal), ((multiple nipples)), ((extra nipples))",
        template_json_file = 'api_panty.json',
        # template_json_file = 'api-sexy.json',
        seed = random.randint(1, 1e14),
        # ckpt_name = 'awportrait_v13.safetensors',
        # ckpt_name = 'meichidarkMix_meichidarkV5.safetensors',
        # height = 768,
        # width = 512,
        # sampler_name = 'dpmpp_2m_sde',
        # scheduler = 'karras',
        steps = 40,
        # cfg = 7,
        # denoise = 1,
        # batch_size = 1,

        # lora_count=1,
        # lora1 = 'sexy-cloth-Tassels-Dudou.safetensors',
        # lora1_wt = 0.85,
        # lora2 = None,
        # lora2_wt = None,
        # lora3 = None,
        # lora3_wt = None,
        # lora4 = None,
        # lora4_wt = None,
    )
    # print(f'args: {args}')
    # t1.send_command(command=Redis_Proxy_Command_T2I.DRAW, args=args)
    t1.send_command(command=Redis_Proxy_Command_T2I.DRAWS, args=args)

    i=0
    for image_data in t1.get_result_gen():
        i += 1
        t1.save_image_to_file(image_data, file_name=f'output_{uuid.uuid4()}')

def main_llm():
    # t1 = Redis_Proxy_Client()
    # t1.new_task(Redis_Task_Type.LLM)
    #
    # args = LLM_Init_Para(url='http://192.168.124.33:8001/v1', max_new_tokens=1024)
    # t1.send_command(command=Redis_Proxy_Command_LLM.INIT, args=args)
    # args = LLM_Ask_Para(question='你是谁？我叫土土', temperature=0.6, system_prompt='你扮演甄嬛', role_prompt='你扮演洪七公')
    # t1.send_command(command=Redis_Proxy_Command_LLM.ASK, args=args)
    # t1.print_stream()

    t2=Redis_Proxy_Client()
    arg1 = LLM_Init_Para(url=config.Domain.llm_url, max_new_tokens=1024)
    arg2 = LLM_Ask_Para(question='你是谁？我叫土土', temperature=0.6, system_prompt='你扮演甄嬛', role_prompt='你扮演洪七公')
    arg3 = LLM_Ask_Para(question='我刚才告诉你我叫什么？', temperature=0.6)
    (t2.new_task(Redis_Task_Type.LLM)
     .send_command(command=Redis_Proxy_Command_LLM.INIT, args=arg1)
     .send_command(command=Redis_Proxy_Command_LLM.ASK, args=arg2)
     .send_command(command=Redis_Proxy_Command_LLM.ASK, args=arg3))
    t2.print_stream()

if __name__ == "__main__":
    main_llm()

    # main_t2i()