from typing import List, Dict, Any, Type, Literal, Optional, Callable
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from uuid import uuid4
from pprint import pprint

import config
from config import dred,dgreen,dcyan,dyellow,dblue,dblack,dwhite
from console import err

from agent.core.resource.protocol import Resource_Data, Resource_Data_Type


DEBUG = config.Global.app_debug

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def dpprint(*args, **kwargs):
    if DEBUG:
        pprint(*args, **kwargs)

class Mem_Resource_Manager:
    # 普通的内存data(dict)
    mem_data_dict:Dict[str, Resource_Data] = {}

    @classmethod
    def get_resource(cls, resource_id):
        # 读取data
        # ------------------mem data load-------------------
        resource_data = cls.mem_data_dict.get(resource_id)
        # -----------------/mem data load-------------------

        return resource_data

    @classmethod
    def set_resource(cls, resource_data:Resource_Data):
        # 生成resource_id
        resource_id = str(uuid4())
        resource_data.resource_id = resource_id

        # 存储data
        # ------------------mem data save-------------------
        cls.mem_data_dict[resource_id] = resource_data
        # -----------------/mem data save-------------------

        return resource_id

def main_mem():
    print('------------Mem_Resource_Manager------------')
    data = Resource_Data(
        data_type=Resource_Data_Type.STRING,
        data='hello'
    )
    rid = Mem_Resource_Manager.set_resource(data)
    print(f'rid={rid!r}')
    data = Mem_Resource_Manager.get_resource(rid)
    print(f'data={data!r}')

    print('-----------/Mem_Resource_Manager------------')

if __name__ == "__main__":
    main_mem()