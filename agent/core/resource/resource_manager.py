from typing import List, Dict, Any, Type, Literal, Optional, Callable
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

from pprint import pprint
import config
from config import dred,dgreen,dcyan,dyellow,dblue,dblack,dwhite
from console import err


DEBUG = config.Global.app_debug

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def dpprint(*args, **kwargs):
    if DEBUG:
        pprint(*args, **kwargs)

class Resource_Data_Type(Enum):
    STRING          = 'string'
    TABLE_STRING    = 'table_string'
    IMAGE           = 'image'
    VIDEO           = 'video'
    AUDIO           = 'audio'
    FILE            = 'file'

class c(BaseModel):
    resource_id     :str
    data_type       :Resource_Data_Type
    data            :Any

class Resource_Manager:
    @classmethod
    def get_resource(cls, resource_id):
        pass

    @classmethod
    def set_resource(cls, resource_data:Resource_Data_Type):
        pass

