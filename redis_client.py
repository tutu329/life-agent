import redis
import json5 as json

from config import Port, dred
from utils.byte_convert import data_convert_from_byte_to_str

from singleton import singleton

from typing import Type, TypeVar

Redis_Client_DEBUG = True
def dprint(*args, **kwargs):
    if Redis_Client_DEBUG:
        print(*args, **kwargs)

T = TypeVar('T')

def from_dict(data_class: Type[T], data: dict) -> T:
    return data_class(**data)

@singleton
class Redis_Client:
    def __init__(self, host='localhost', port=Port.redis):
        self.host = host
        self.port = port

        self.__client = None

    def __connect(self):
        if self.__client is None:
            try:
                self.__client = redis.Redis(host=self.host, port=self.port, db=0)
            except redis.exceptions.TimeoutError as e:
                dred(f'Redis_Client.connect(): failed.({e})')
                self.__client = None

    def set(self, key, value_string):
        self.__connect()

        try:
            self.__client.set(key, value_string)
        except redis.exceptions.TimeoutError as e:
            dred(f'Redis_Client.set(key={key}, value={value_string}): failed.({e})')
            self.__client = None

    def get(self, key):
        self.__connect()

        try:
            return self.__client.get(key)
        except redis.exceptions.TimeoutError as e:
            dred(f'Redis_Client.get(key={key}): failed.({e})')
            self.__client = None
            return None

    def set_dict(self, key, value_dict):
        self.__connect()

        try:
            self.__client.set(key, json.dumps(value_dict))
        except redis.exceptions.TimeoutError as e:
            dred(f'Redis_Client.set_dict(key={key}, value={value_dict}): failed.({e})')
            self.__client = None

    def get_dict(self, key):
        self.__connect()

        try:
            return json.loads(self.__client.get(key))
        except redis.exceptions.TimeoutError as e:
            dred(f'Redis_Client.get_dict(key={key}): failed.({e})')
            self.__client = None
            return None

    def add_stream(
            self,
            stream_key,
            data
    ) -> str:                   # 返回message_id
        # 向流中添加消息
        # message_id = self.__client.xadd(stream_key, {'key1': 'value1', 'key2': 'value2'})
        message_id = self.__client.xadd(stream_key, data)
        dprint(f'Message added with ID: {message_id}')
        return message_id

    def pop_stream(
            self,
            stream_key,
            inout_data_list,    # 返回的数据列表
            use_byte=False,     # 是否使用byte格式的数据(b'xxx')
            last_id='0-0',      # 起始id(>该id，则返回)
            count=100,          # 返回数据个数
            block=100           # 阻塞时间ms
    ) -> str:   # 返回last_id
        # 读取新的消息
        messages = self.__client.xread({stream_key: last_id}, count=count, block=block)
        # print(f'messages: {messages}')

        if messages:
            for message in messages[0][1]:
                message_id = message[0]
                message_data = message[1]
                if inout_data_list is not None:
                    if use_byte:
                        inout_data_list.append(message_data)
                    else:
                        inout_data_list.append(data_convert_from_byte_to_str(message_data))
                    dprint(f'\t Received message ID: {message_id}, data: {message_data}', end='', flush=True)

                # 更新 last_id 以避免重复读取
                last_id = message_id.decode('utf-8')
                dprint(f'\t msg id: "{last_id}"')
            dprint()
            return last_id
        else:
            return None

    # 定义一个函数来处理字节字符串


def main():
    # client = Redis_Client(host='116.62.63.201')

    # client = Redis_Client(host='localhost')
    client = Redis_Client(host='192.168.124.33')
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

    # r = redis.Redis(host='116.62.63.201')
    # r.set('msg', 'hh')


if __name__ == "__main__":
    main()