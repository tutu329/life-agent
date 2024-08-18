import redis
import json5 as json

import config
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

# @singleton
class Redis_Client:
    s_stream_last_ids = {
        # 'stream_key1': 'stream_last_id1',
        # 'stream_key2': 'stream_last_id2',
    }

    def __init__(
            self,
            host=config.Domain.redis_server_domain,       # domain
            port=Port.redis_client,        # port
            invoker=None,           # 调用方如‘redis_proxy_server’
            password='',            # 密码
            ssl=True,  # 是否通过ssl/tls连接
            ssl_keyfile='d:\\models\\powerai.key',
            ssl_certfile='d:\\models\\powerai_public.crt',
    ):
        if invoker is not None:
            print(f'【Redis_Client inited with invoker】{invoker}')
        # print(f'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@host:{host}@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
        self.host = host
        self.port = port
        self.password = password
        self.ssl = ssl
        self.ssl_keyfile = ssl_keyfile
        self.ssl_certfile = ssl_certfile

        self._client = None

    def _connect(self):
        if self._client is None:
            try:
                if self.ssl:
                    self._client = redis.StrictRedis(
                        host=self.host,
                        port=self.port,
                        password=self.password,
                        ssl=True,
                        ssl_keyfile=self.ssl_keyfile,
                        ssl_certfile=self.ssl_certfile,
                    )
                else:
                    self._client = redis.Redis(
                        host=self.host,
                        port=self.port,
                        db=0
                    )
            except redis.exceptions.TimeoutError as e:
                dred(f'Redis_Client.connect(): failed.({e})')
                self._client = None

    def flushall(self):
        self._connect()
        self._client.flushall()

    def set_string(self, key, value_string):
        self._connect()

        try:
            self._client.set(key, value_string)
        except redis.exceptions.TimeoutError as e:
            dred(f'Redis_Client.set(key={key}, value={value_string}): failed.({e})')
            self._client = None

    def get_string(self, key):
        self._connect()

        try:
            result = self._client.get(key)
            if result:
                return result.decode('utf-8')
            else:
                return ''
        except redis.exceptions.TimeoutError as e:
            dred(f'Redis_Client.get(key={key}): failed.({e})')
            self._client = None
            return None

    def set_dict(self, key, value_dict):
        self._connect()

        try:
            self._client.set(key, json.dumps(value_dict))
        except redis.exceptions.TimeoutError as e:
            dred(f'Redis_Client.set_dict(key={key}, value={value_dict}): failed.({e})')
            self._client = None

    def get_dict(self, key):
        self._connect()

        try:
            string = self._client.get(key)
            # print(f'string: {string}')
            if string:
                return json.loads(string)
            else:
                return {}
        except redis.exceptions.TimeoutError as e:
            dred(f'Redis_Client.get_dict(key={key}): failed.({e})')
            self._client = None
            return {}

    def add_stream(
            self,
            stream_key,
            data
    ) -> str:                   # 返回message_id
        self._connect()

        # 向流中添加消息
        # message_id = self.__client.xadd(stream_key, {'key1': 'value1', 'key2': 'value2'})
        message_id = self._client.xadd(stream_key, data)
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
        self._connect()

        # 处理stream_key下的stream_last_id
        if stream_key in self.s_stream_last_ids:
            last_id = self.s_stream_last_ids[stream_key]
        else:
            last_id = '0-0'

        # 读取新的消息
        messages = self._client.xread({stream_key: last_id}, count=count, block=block)
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

    client = Redis_Client(host='172.27.67.106', port=6380)  # win-server
    # client = Redis_Client(host='localhost', port=6379)  # win-server
    # client = Redis_Client(host='192.168.124.33', port=8010)  # ubuntu-server
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

def tls_test():
    import redis
    import ssl

    # 配置连接参数
    redis_host = 'powerai.cc'
    # redis_host = '172.27.67.106'
    redis_port = 8010  # 假设 Redis 使用的是启用 TLS 的端口
    redis_password = ''  # 如果 Redis 设置了密码，请填写此处

    # 创建 Redis 连接对象
    redis_client = redis.StrictRedis(
        host=redis_host,
        port=redis_port,
        password=redis_password,
        ssl=True,
        # ssl_cert_reqs=None,
        # ssl_cert_reqs='required',

        ssl_keyfile='d:\\models\\powerai.key',
        ssl_certfile='d:\\models\\powerai_public.crt',
        # ssl_cert_reqs=ssl.CERT_REQUIRED,
    )
    print(redis_client)

    # 测试连接
    try:
        pong = redis_client.ping()
        if pong:
            print('Connected to Redis server with SSL/TLS successfully!')

        key_set = 'msg'
        content_set = '欢迎来到redis tls.'
        print(f'\t设置     ：key[{key_set}], value[{content_set}]')
        redis_client.set(key_set, content_set)
        rtn1 = redis_client.get(key_set)
        rtn2 = redis_client.get(key_set).decode('utf-8')
        print(f'\t读取  raw: key[{key_set}], value[{rtn1}]')
        print(f'\t读取 utf8: key[{key_set}], value[{rtn2}]')
        print('python以tls方式，访问redis-stack-servertls成功！')

    except Exception as e:
        print(f'Error connecting to Redis server: {e}')

if __name__ == "__main__":
    # main()

    # tls_test()

    r = Redis_Client()
    r.set_string('client_string1', '你是谁')
    print(r.get_string('client_string1'))