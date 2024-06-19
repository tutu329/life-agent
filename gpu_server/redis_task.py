from utils.task import Task_Base, Status
from redis_client import Redis_Client

import uuid,time

class Redis_Task_Server(Task_Base):
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

def main():
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

def Example_Callback(out_task_info, arg1):
    i=arg1
    while True:
        i += 1
        if out_task_info['status']==Status.Cancelling:
             print(f"{out_task_info['task_name']} cancelled")
             break
        print(i)
        time.sleep(1)

def main1():
    t = Redis_Task_Server()
    t.init(Example_Callback, in_name='task1', in_timeout=3, arg1=100)
    t.start()

if __name__ == "__main__":
    main1()
    # main()