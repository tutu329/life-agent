from redis_proxy.redis_proxy_client import Redis_Task_Type, Redis_LLM_Command
from redis_proxy.redis_proxy_client import Redis_Proxy_Client

def main():
    # c = Redis_Task_Client()
    # c.add_llm_task('2+2=')

    t1 = Redis_Proxy_Client()
    task_id = t1.new_task(str(Redis_Task_Type.LLM))
    t1.send_command(task_id=task_id, command=str(Redis_LLM_Command.INIT), url='http://192.168.124.33:8001/v1', max_new_tokens=1024)
    t1.send_command(task_id=task_id, command=str(Redis_LLM_Command.ASK), question='写一首长诗', temperature=0.8)
    # t1.send_command(task_id=task_id, command=str(Redis_LLM_Command.ASK), question='1+1=?', temperature=0.7)
    print(f'result is : {t1.get_result_gen(task_id=task_id)}')
    print(f'status is : {t1.get_status(task_id=task_id)}')
    import time

    print(f'result is:')
    for chunk in t1.get_result_gen(task_id):
        print(chunk, end='', flush=True)

if __name__ == "__main__":
    main()