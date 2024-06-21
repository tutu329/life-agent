from redis_proxy.redis_proxy_client import Redis_Task_Type, Redis_LLM_Command
from redis_proxy.redis_proxy_client import Redis_Proxy_Client

def main():
    # c = Redis_Task_Client()
    # c.add_llm_task('2+2=')

    t1 = Redis_Proxy_Client()
    task_id = t1.new_task(str(Redis_Task_Type.LLM))
    t1.send_command(task_id=task_id, command=str(Redis_LLM_Command.INIT), url='http://192.168.124.33:8001/v1', max_new_tokens=1024)
    t1.send_command(task_id=task_id, command=str(Redis_LLM_Command.ASK), question='你是谁？我叫土土', temperature=0.6, system_prompt='你扮演甄嬛', role_prompt='你扮演洪七公')
    print(f'result is:')
    for chunk in t1.get_result_gen(task_id):
        print(chunk, end='', flush=True)
    print()

    t1.send_command(task_id=task_id, command=str(Redis_LLM_Command.ASK), question='我叫什么', temperature=0.7)

    print(f'result is:')
    for chunk in t1.get_result_gen(task_id):
        print(chunk, end='', flush=True)
    print()

if __name__ == "__main__":
    main()