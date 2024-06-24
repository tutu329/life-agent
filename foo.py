from redis_proxy.command.protocol import Redis_Task_Type
from redis_proxy.command.llm.protocol import Redis_Proxy_Command_LLM
from redis_proxy.redis_proxy_client import Redis_Proxy_Client

from redis_proxy.command.llm.protocol import LLM_Ask_Para, LLM_Init_Para


def main():
    # c = Redis_Task_Client()
    # c.add_llm_task('2+2=')

    t1 = Redis_Proxy_Client()
    task_id = t1.new_task(str(Redis_Task_Type.LLM))

    args = LLM_Init_Para(url='http://192.168.124.33:8001/v1', max_new_tokens=1024)
    t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_LLM.INIT), args=args)
    # t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_LLM.INIT), url='http://192.168.124.33:8001/v1', max_new_tokens=1024)

    args = LLM_Ask_Para(question='你是谁？我叫土土', temperature=0.6, system_prompt='你扮演甄嬛', role_prompt='你扮演洪七公')
    t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_LLM.ASK), args=args)
    # t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_LLM.ASK), question='你是谁？我叫土土', temperature=0.6, system_prompt='你扮演甄嬛', role_prompt='你扮演洪七公')
    print(f'result is:')
    for chunk in t1.get_result_gen(task_id):
        print(chunk, end='', flush=True)
    print()


    args = LLM_Ask_Para(question='写一首藏头诗', temperature=0.7)
    t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_LLM.ASK), args=args)
    # t1.send_command(task_id=task_id, command=str(Redis_Proxy_Command_LLM.ASK), question='写一首长诗', temperature=0.7)

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

if __name__ == "__main__":
    main()