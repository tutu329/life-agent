from redis_client import Redis_Client

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

if __name__ == "__main__":
    main()