from redis_proxy.custom_command.protocol import Redis_Task_Type
from redis_proxy.redis_proxy_client import Redis_Proxy_Client

from redis_proxy.custom_command.llm.protocol import Redis_Proxy_Command_LLM, LLM_Ask_Para, LLM_Init_Para
from redis_proxy.custom_command.t2i.protocol import Redis_Proxy_Command_T2I, T2I_Init_Para, T2I_Draw_Para

import random

def main():
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
    print(f'result is:')
    for chunk in t1.get_result_gen(task_id):
        print(chunk, end='', flush=True)
    print()


    args = LLM_Ask_Para(question='写一首藏头诗', temperature=0.7)
    t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_LLM.ASK), args=args)
    # t1.send_command(task_id=task_id, custom_command=str(Redis_Proxy_Command_LLM.ASK), question='写一首长诗', temperature=0.7)

    print(f'result is:')
    result = ''
    for chunk in t1.get_result_gen(task_id):
        result += chunk
        print(chunk, end='', flush=True)
        if len(result)>50:
            t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_LLM.CANCEL))
            print()
            print('canceled.')
            break

    print()

def main_t2i():
    t1 = Redis_Proxy_Client()
    task_id = t1.new_task(str(Redis_Task_Type.T2I))

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
        positive='masterpiece,best quality,absurdres,highres,4k,ray tracing,perfect face,perfect eyes,intricate details,highly detailed, 1girl,(breasts:1.2),moyou,looking at viewer,sexy pose,(cowboy shot:1.2), <lora:Tassels Dudou:0.8>,Tassels Dudou,white dress,back,',
        negative='EasyNegativeV2,(badhandv4:1.2),bad-picture-chill-75v,BadDream,(UnrealisticDream:1.2),bad_prompt_v2,NegfeetV2,ng_deepnegative_v1_75t,ugly,(worst quality:2),(low quality:2),(normal quality:2),lowres,watermark,',
        template_json_file = 'api-sexy.json',
        seed = random.randint(1, 1e14),
        ckpt_name = 'meichidarkMix_meichidarkV5.safetensors',
        height = 768,
        width = 512,
        sampler_name = 'dpmpp_2m_sde',
        scheduler = 'karras',
        steps = 72,
        cfg = 7,
        denoise = 1,
        batch_size = 1,

        lora_count=1,
        lora1 = 'sexy-cloth-Tassels-Dudou.safetensors',
        lora1_wt = 0.85,
        lora2 = None,
        lora2_wt = None,
        lora3 = None,
        lora3_wt = None,
        lora4 = None,
        lora4_wt = None,
    )
    # print(f'args: {args}')
    # t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_T2I.DRAW), args=args)
    t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_T2I.DRAWS), args=args)

    i=0
    for image_data in t1.get_result_gen(task_id):
        i += 1
        t1.save_image_to_file(image_data, file_name=f'output_{task_id}_{i}')


if __name__ == "__main__":
    main_t2i()
    # main()