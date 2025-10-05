from typing import List, Dict, Any, Type, Literal, Optional, Callable
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class Resource_Data_Type(Enum):
    STRING          = 'string'
    TABLE_STRING    = 'table_string'
    IMAGE           = 'image'
    VIDEO           = 'video'
    AUDIO           = 'audio'
    FILE            = 'file'

class Resource_Data(BaseModel):
    resource_id     :str = ''               # resource_id由server生成
    data_type       :Resource_Data_Type
    data            :Any