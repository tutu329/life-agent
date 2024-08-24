from enum import Enum, unique
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any

import config


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
    url:str = config.LLM_Default.url
    history:bool = config.LLM_Default.history
    max_new_tokens:int = config.LLM_Default.max_new_tokens
    temperature:float = config.LLM_Default.temperature
    api_key:str = config.LLM_Default.api_key

# LLM调用(Ask)参数
@dataclass
class LLM_Ask_Para():
    question:str = ''

    temperature:float = config.LLM_Default.temperature
    max_new_tokens:int = config.LLM_Default.max_new_tokens
    stream:bool = config.LLM_Default.stream

    clear_history:bool = config.LLM_Default.clear_history
    system_prompt:Any = None
    role_prompt:Any = None