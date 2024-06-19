from utils.task import Task_Base, Status
from redis_client import Redis_Client
from config import dred,dgreen

import uuid,time

class Task(Task_Base):
    def __init__(self):
        super().__init__()

    def init(self,
             in_callback_func,
             *in_callback_func_args,
             in_name='redis_task_'+str(uuid.uuid4()),
             in_timeout=None,    # timeout秒之后，设置cancel标识
             in_streamlit=False,
             **in_callback_func_kwargs
            ):
        super().init(
             in_callback_func,
             *in_callback_func_args,
             in_name=in_name,
             in_timeout=in_timeout,
             in_streamlit=in_streamlit,
             **in_callback_func_kwargs
        )

    def start(self):
        super().start()

def redis_test():
    client = Redis_Client(host='localhost', port=6379)  # win-server

    # client = Redis_Client(host='192.168.124.33')  # ubuntu-server
    d = {
        'aa':22,
        'bb':11,
    }
    client.set_dict('msg', d)
    print(client.get_dict('msg'))
    print('ssss')

    inout_list1 = []
    inout_list2 = []
    client.add_stream('test_stream', data={'name':'jack', 'age':35})
    last1 = client.pop_stream('test_stream', inout_data_list=inout_list1)
    last2 = client.pop_stream('test_stream', use_byte=False, inout_data_list=inout_list2,  last_id='1718178990332-0', count=2)

    print(f'last1: {last1}')
    print(f'inout_list1: "{inout_list1}')
    print(f'last2: {last2}')
    print(f'inout_list2: "{inout_list2}')

def Redis_Task_Server_Callback(out_task_info_must_be_here):
    i=900
    while True:
        i += 1
        if out_task_info_must_be_here['status']==Status.Cancelling:
             print(f"{out_task_info_must_be_here['task_name']} cancelled")
             break
        print(f'Redis Task Server: {i}')
        time.sleep(1)

s_redis_task_server = Task()
s_redis_task_server.init(Redis_Task_Server_Callback)
# s_redis_task_server.init(Redis_Task_Server_Callback, in_timeout=3)
s_redis_task_server.start()
dgreen(f'Redis Task Server started.')

def Example_Callback(out_task_info_must_be_here, num, num2):
    i=num
    while True:
        i += 1
        if out_task_info_must_be_here['status']==Status.Cancelling:
             print(f"{out_task_info_must_be_here['task_name']} cancelled")
             break
        print(i)
        # print(out_task_info_must_be_here)
        time.sleep(1)

def main():
    t = Task()
    t.init(Example_Callback, in_timeout=3, num=100, num2=300)
    t.start()
    while(1):
        time.sleep(1)

if __name__ == "__main__":
    main()
    # redis_test()