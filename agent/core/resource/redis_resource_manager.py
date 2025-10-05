 # 安装redis服务
#     sudo apt install redis-server
#     sudo systemctl start redis-server
#     sudo systemctl restart redis-server
#     sudo systemctl enable redis-server
#     sudo systemctl status redis-server
#
# 配置redis
#     sudo vi /etc/redis/redis.conf
#     bind 127.0.0.1 改为 bind 0.0.0.0
#     port 6379 改为 8010(https时，是tls-port设置为8010)
#     sudo systemctl restart redis-server
#     验证：
#         redis-cli -p 8010
#         ping（如果返回PONG则正常）
#
# win下安装redis-cli
#     https://github.com/microsoftarchive/redis/releases下载最新msi，安装即可
#     控制台下验证：
#         redis-cli -h powerai.cc -p 8010
#         ping（如果返回PONG则正常）
#
# 关于TLS(https)：
#     1、sudo cat /etc/redis/redis.conf | grep tls
#     2、确保crt和key文件没有过期
#     3、redis-cli --tls -h powerai.cc -p 8010 --cacert /etc/ssl/certs/ca-certificates.crt -a 'YOUR_STRONG_PASS' PING
#     4、取消TLS，/etc/redis/redis.conf中，注释掉所有tls开头的配置，port 0改为port 8010

from uuid import uuid4
from pprint import pprint
import json

import config
from config import dred,dgreen,dcyan,dyellow,dblue,dblack,dwhite
from console import err

from redis_client import Redis_Client
from agent.core.resource.protocol import Resource_Data, Resource_Data_Type

DEBUG = config.Global.app_debug

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def dpprint(*args, **kwargs):
    if DEBUG:
        pprint(*args, **kwargs)

class Redis_Resource_Manager:
    redis_client = Redis_Client(host='powerai.cc', ssl=False)
    @classmethod
    def get_resource(cls, resource_id)->Resource_Data:
        # 读取data
        # ------------------redis data load-------------------
        data_str = cls.redis_client.get_string(key=resource_id)
        json_data = json.loads(data_str)
        resource_data = Resource_Data(**json_data)
        # -----------------/redis data load-------------------

        return resource_data

    @classmethod
    def get_resource_json(cls, resource_id):
        # 读取data
        # ------------------redis data load-------------------
        resource_data_json = cls.redis_client.get_string(key=resource_id)
        # -----------------/redis data load-------------------

        return resource_data_json

    @classmethod
    def set_resource(cls, resource_data:Resource_Data):
        # 生成resource_id
        resource_id = str(uuid4())
        resource_data.resource_id = resource_id

        # 存储data
        # ------------------redis data save-------------------
        data_str = json.dumps(resource_data.model_dump(), ensure_ascii=False)
        cls.redis_client.set_string(key=resource_id, value_string=data_str)
        # -----------------/redis data save-------------------

        return resource_id

def main_redis():
    print('------------Redis_Resource_Manager------------')
    data = Resource_Data(
        data_type=Resource_Data_Type.STRING,
        data={'content':'hello'}
    )
    rid = Redis_Resource_Manager.set_resource(data)
    print(f'rid={rid!r}')
    data = Redis_Resource_Manager.get_resource(rid)
    print(f'resource_data={data!r}')

    data_json = Redis_Resource_Manager.get_resource_json(rid)
    print(f'resource_data_json={data_json!r}')

    print('-----------/Redis_Resource_Manager------------')

if __name__ == "__main__":
    main_redis()

    # r = Redis_Client(ssl=False)
    # r.set_string('client_string1', '你是谁')
    # print(r.get_string('client_string1'))