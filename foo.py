from redis_proxy.redis_proxy_server import Redis_Task_Type, Redis_LLM_Command

from redis_proxy.redis_proxy_client import Redis_Proxy_Client
# from redis_proxy.redis_proxy_client import Redis_Task_Client

# def redis_test():
#     client = Redis_Client(host='192.168.124.33', port=8010)  # win-server
#     # client = Redis_Client(host='localhost', port=6379)  # win-server
#
#
#     inout_list1 = []
#     inout_list2 = []
#     data = Redis_Task_LLM_Data()
#     data.task_type = str(Redis_Task_Type.LLM)
#     data.task_input = '你是谁？'
#     print(f'data: {data}')
#     client.add_stream('redis_task', data=asdict(data))
#     # last1 = client.pop_stream('test_stream', inout_data_list=inout_list1)
#     # last2 = client.pop_stream('test_stream', use_byte=False, inout_data_list=inout_list2,  last_id='1718178990332-0', count=2)
#
#     # print(f'last1: {last1}')
#     # print(f'inout_list1: "{inout_list1}')
#     # print(f'last2: {last2}')
#     # print(f'inout_list2: "{inout_list2}')

def main():
    # c = Redis_Task_Client()
    # c.add_llm_task('2+2=')

    t1 = Redis_Proxy_Client()
    task_id = t1.new_task(str(Redis_Task_Type.LLM))
    t1.send_command(task_id=task_id, command=str(Redis_LLM_Command.INIT), url='http://192.168.124.33:8001/v1', max_new_tokens=1024)
    t1.send_command(task_id=task_id, command=str(Redis_LLM_Command.ASK), question='你是谁', temperature=0.8)
    # t1.send_command(task_id=task_id, command=str(Redis_LLM_Command.ASK), question='1+1=?', temperature=0.7)
    print(f'result is : {t1.get_result(task_id=task_id)}')
    print(f'status is : {t1.get_status(task_id=task_id)}')
    import time

    print(f'result is:')
    while True:
        print(t1.get_result(task_id))
        # print(t1.get_result(task_id), end='\r', flush=True)
        # time.sleep(0.2)
        if t1.get_status(task_id)=='completed':
            print('finished.')
            break


if __name__ == "__main__":
    main()