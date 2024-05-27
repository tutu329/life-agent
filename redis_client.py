import redis
import json5 as json

from config import Port
from singleton import singleton

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
                print(f'Redis_Client.connect(): failed.({e})')
                self.__client = None

    def set(self, key, value_string):
        self.__connect()

        try:
            self.__client.set(key, value_string)
        except redis.exceptions.TimeoutError as e:
            print(f'Redis_Client.set(key={key}, value={value_string}): failed.({e})')
            self.__client = None

    def get(self, key):
        self.__connect()

        try:
            return self.__client.get(key)
        except redis.exceptions.TimeoutError as e:
            print(f'Redis_Client.get(key={key}): failed.({e})')
            self.__client = None
            return None

    def set_dict(self, key, value_dict):
        self.__connect()

        try:
            self.__client.set(key, json.dumps(value_dict))
        except redis.exceptions.TimeoutError as e:
            print(f'Redis_Client.set_dict(key={key}, value={value_dict}): failed.({e})')
            self.__client = None

    def get_dict(self, key):
        self.__connect()

        try:
            return json.loads(self.__client.get(key))
        except redis.exceptions.TimeoutError as e:
            print(f'Redis_Client.get_dict(key={key}): failed.({e})')
            self.__client = None
            return None
def main():
    # client = Redis_Client(host='116.62.63.201')

    client = Redis_Client()
    # client = Redis_Client(host='192.168.124.33')
    d = {
        'aa':22,
        'bb':11,
    }
    client.set_dict('msg', d)
    print(client.get_dict('msg'))
    print('ssss')

    # r = redis.Redis(host='116.62.63.201')
    # r.set('msg', 'hh')

if __name__ == "__main__":
    main()