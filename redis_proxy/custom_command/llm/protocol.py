from enum import Enum, unique
from typing import List, Any
from dataclasses import dataclass, asdict, field

@dataclass
class Config():
    command_parallel: bool = False

# LLM命令
@unique
class Redis_Proxy_Command_LLM(Enum):
    INIT    = 'INIT'
    # START = 'START'
    CANCEL  = 'CANCEL'
    ASK     = 'ASK'

# LLM调用(Init)参数
@dataclass
class LLM_Init_Para():
    url:str = ''
    history:bool = True     # bool传给redis前，会被redis_proxy_client转换为Int
    max_new_tokens:int = 1024
    temperature:float = 0.7
    api_key:str = 'empty'

# LLM调用(Ask)参数
@dataclass
class LLM_Ask_Para():
    question:str = ''

    temperature:Any = None
    max_new_tokens:Any = None
    stream:Any = None
    stops:Any = None

    clear_history:Any = None
    system_prompt:Any = None
    role_prompt:Any = None