from typing import List, Dict, Any, Type
from pydantic import BaseModel, Field, ConfigDict
from queue import Queue

class Agent_Status(BaseModel):
    started:bool    = False
    canceling:bool  = False
    canceled:bool   = False
    finished:bool   = False

class Agent_Stream_Queue(BaseModel):
    output          :Queue= Field(default_factory=Queue)
    thinking        :Queue= Field(default_factory=Queue)
    log             :Queue= Field(default_factory=Queue)
    tool_rtn_data   :Queue= Field(default_factory=Queue)

    # 开启“任意类型”支持
    model_config = ConfigDict(arbitrary_types_allowed=True)