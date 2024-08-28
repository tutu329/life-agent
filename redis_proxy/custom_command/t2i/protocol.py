from enum import Enum, unique
from typing import List, Any
from dataclasses import dataclass, asdict, field

# T2I命令
@unique
class Redis_Proxy_Command_T2I(Enum):
    INIT    = 'INIT'
    DRAW    = 'DRAW'
    DRAWS   = 'DRAWS'


# T2I调用(Init)参数
@dataclass
class T2I_Init_Para():
    url:str = ''    # url='localhost:5100'

# T2i调用(Draw)参数
@dataclass
class T2I_Draw_Para():
    using_template:int = 1      # 由于redis，不能用bool

    positive:str = ''
    negative:Any = None

    template_json_file:Any = None
    seed:Any = None
    ckpt_name:Any = None
    height:Any = None
    width:Any = None
    sampler_name:Any = None
    scheduler:Any = None
    steps:Any = None
    cfg:Any = None
    denoise:Any = None
    batch_size:Any = None

    lora_count:Any = None
    lora1:Any = None
    lora1_wt:Any = None
    lora2:Any = None
    lora2_wt:Any = None
    lora3:Any = None
    lora3_wt:Any = None
    lora4:Any = None
    lora4_wt:Any = None