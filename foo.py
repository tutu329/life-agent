from dataclasses import dataclass, asdict, field
from redis_client import Redis_Client

from gpu_server.redis_task import *

def redis_test():
    client = Redis_Client(host='192.168.124.33', port=8010)  # win-server
    # client = Redis_Client(host='localhost', port=6379)  # win-server


    inout_list1 = []
    inout_list2 = []
    data = Redis_Task_LLM_Data()
    data.task_type = str(Redis_Task_Type.LLM)
    data.task_input = '你是谁？'
    print(f'data: {data}')
    client.add_stream('redis_task', data=asdict(data))
    # last1 = client.pop_stream('test_stream', inout_data_list=inout_list1)
    # last2 = client.pop_stream('test_stream', use_byte=False, inout_data_list=inout_list2,  last_id='1718178990332-0', count=2)

    # print(f'last1: {last1}')
    # print(f'inout_list1: "{inout_list1}')
    # print(f'last2: {last2}')
    # print(f'inout_list2: "{inout_list2}')

def main():
    c = Redis_Task_Client()
    c.add_llm_task('1+1=')

if __name__ == "__main__":

    # print(f'type is : {str(Redis_Task_Type.LLM)}')
    # redis_test()
    main()