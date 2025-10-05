from typing import List, Dict, Any, Type, Literal, Optional, Callable
from pydantic import BaseModel, Field, ConfigDict

class Resource_Data_Type:
    STRING          = 'string'
    TABLE_STRING    = 'table_string'
    IMAGE           = 'image'
    VIDEO           = 'video'
    AUDIO           = 'audio'
    FILE            = 'file'

class Resource_Data(BaseModel):
    resource_id     :str = ''               # resource_id由server生成
    data_type       :str                    # 枚举直接用普通class映射到str，不用Enum类，否则无法json序列化
    data            :Any