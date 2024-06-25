from enum import Enum, unique
from typing import List, Any
from dataclasses import dataclass, asdict, field

# T2I命令
@unique
class Redis_Proxy_Command_T2I(Enum):
    INIT    = 'INIT'
    DRAW    = 'DRAW'

# T2I调用(Init)参数
@dataclass
class T2I_Init_Para():
    url:str = ''    # url='localhost:5100'

# T2i调用(Draw)参数
@dataclass
class T2I_Draw_Para():
    positive:str = ''
    negative:str = ''

    ckpt_name:Any = None
    height:Any = None
    width:Any = None
    seed:Any = None
