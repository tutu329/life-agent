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
    args = T2I_Draw_Para(
        positive='8k raw, photo, masterpiece, super man',
        negative='ugly',
        seed=seed,
        ckpt_name='sdxl_lightning_2step.safetensors',
        height=1024,
        width=1024,
    )
    t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_T2I.DRAW), args=args)

    i=0
    for image_data in t1.get_result_gen(task_id):
        i += 1
        t1.save_image_to_file(image_data, file_name=f'output_{task_id}_{i}')


if __name__ == "__main__":
    main_t2i()
    # main()