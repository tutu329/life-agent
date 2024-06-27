import redis
import json5 as json

from config import Port, dred
from utils.byte_convert import data_convert_from_byte_to_str

from singleton import singleton

from typing import Type, TypeVar, List, Dict

Redis_Client_DEBUG = False
def dprint(*args, **kwargs):
    if Redis_Client_DEBUG:
        print(*args, **kwargs)

T = TypeVar('T')

def from_dict(data_class: Type[T], data: dict) -> T:
    return data_class(**data)

@singleton
class Redis_Client:
    s_stream_last_ids = {
        # 'stream_key1': 'stream_last_id1',
        # 'stream_key2': 'stream_last_id2',
    }

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

    def flushall(self):
        self.__connect()
        self.__client.flushall()

    def set_string(self, key, value_string):
        self.__connect()

        try:
            self.__client.set(key, value_string)
        except redis.exceptions.TimeoutError as e:
            dred(f'Redis_Client.set(key={key}, value={value_string}): failed.({e})')
            self.__client = None

    def get_string(self, key):
        self.__connect()

        try:
            result = self.__client.get(key)
            if result:
                return result.decode('utf-8')
            else:
                return ''
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
            string = self.__client.get(key)
            # print(f'string: {string}')
            if string:
                return json.loads(string)
            else:
                return {}
        except redis.exceptions.TimeoutError as e:
            dred(f'Redis_Client.get_dict(key={key}): failed.({e})')
            self.__client = None
            return {}

    def add_stream(
            self,
            stream_key,
            data
    ) -> str:                   # 返回message_id
        self.__connect()

        # 向流中添加消息
        # message_id = self.__client.xadd(stream_key, {'key1': 'value1', 'key2': 'value2'})
        message_id = self.__client.xadd(stream_key, data)
        dprint(f'Message added with ID: {message_id}')
        return message_id

    def pop_stream(
            self,
            stream_key,
            # inout_data_list,    # 返回的数据列表
            use_byte=False,     # 是否使用byte格式的数据(b'xxx')
            # last_id='0-0',      # 起始id(>该id，则返回)
            count=100,          # 返回数据个数
            block=100           # 阻塞时间ms
    ) -> List[Dict]:   # 返回last_id
        self.__connect()

        # 处理stream_key下的stream_last_id
        if stream_key in self.s_stream_last_ids:
            last_id = self.s_stream_last_ids[stream_key]
        else:
            last_id = '0-0'

        # 读取新的消息
        messages = self.__client.xread({stream_key: last_id}, count=count, block=block)
        # print(f'messages: {messages}')

        rtn_data_list = []

        if messages:
            for message in messages[0][1]:
                message_id = message[0]
                message_data = message[1]

                # print(f'---------------------------------------------')
                # for k, v in message_data.items():
                #     if len(v)>100:
                #         print(f'\t {k}: {v[:10]}...(len: {len(v)})')
                #     else:
                #         print(f'\t {k}: {v}')

                if use_byte:
                    rtn_data_list.append(message_data)
                else:
                    rtn_data_list.append(data_convert_from_byte_to_str(message_data))
                dprint(f'\t Received message ID: {message_id}, data: {message_data}', end='', flush=True)

                # 更新 last_id 以避免重复读取
                last_id = message_id.decode('utf-8')
                self.s_stream_last_ids[stream_key] = last_id
                dprint(f'\t msg id: "{last_id}"')
            dprint()

        return rtn_data_list

def main():
    # client = Redis_Client(host='116.62.63.201')

    # client = Redis_Client(host='localhost')

    # client = Redis_Client(host='localhost', port=6379)  # win-server
    client = Redis_Client(host='192.168.124.33', port=8010)  # ubuntu-server
    d = {
        'aa':22,
        'bb':11,
    }
    client.set_dict('msg', d)
    print(client.get_dict('msg'))
    print('ssss')

    client.add_stream('test_stream', data={'name':'jack', 'age':35})
    client.add_stream('test_stream', data={'name':'jack', 'age':36})
    client.add_stream('test_stream', data={'name':'jack', 'age':37})
    dict1 = client.pop_stream('test_stream')
    dict2 = client.pop_stream('test_stream', use_byte=False)

    print(f'dict1: {dict1}')
    print(f'dict2: {dict2}')

    # r = redis.Redis(host='116.62.63.201')
    # r.set('msg', 'hh')


if __name__ == "__main__":
    main()