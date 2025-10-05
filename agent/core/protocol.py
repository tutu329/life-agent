from typing import List, Dict, Any, Type, Optional
from pydantic import BaseModel, Field, ConfigDict
from queue import Queue
from threading import Thread
from enum import Enum

from agent.core.resource.protocol import Resource_Data

class Agent_Tool_Result(BaseModel):
    result_summary      :str                                # tool调用生成的结果(摘要)
    result_resource_id  :Optional[str] = None               # tool调用生成的结果的resource_id, 与tool_call_id对应
    # result_data         :Optional[Resource_Data] = None     # tool调用生成的结果数据

class Agent_Request_Type(Enum):
    CREATE = 'create'
    RUN = 'run'
    WAIT = 'wait'
    CANCEL = 'cancel'
    GET_STATUS = 'get_status'
    CLEAR_HISTORY = 'clear_history'

class Agent_Request_Result_Type(Enum):
    SUCCESS = 'success'
    FAILED = 'failed'

class Agent_Request_Result(BaseModel):
    agent_id        : str
    request_type    : Agent_Request_Type
    result_type     : Agent_Request_Result_Type
    result_string   : str = ''
    result_content  : Any = {}

class Agent_Status(BaseModel):
    started             :bool = False   # agent是否created
    querying            :bool = False   # agent是否正在query

    canceling           :bool = False   # agent的query是否正在canceling
    canceled            :bool = False   # agent的query是否canceled

    query_task_finished :bool = False   # agent是否完成了一轮query

    final_answer        :str = ''       # agent的query任务的最终answer

class Agent_Data(BaseModel):
    agent_id:       str
    agent:          Any = None      # agent对象
    agent_thread:   Optional[Thread] = Field(default=None, exclude=True, repr=False)  # 该变量不出现在model_dump()和str中
    model_config = ConfigDict(arbitrary_types_allowed=True)

class Agent_Stream_Queues(BaseModel):
    output          :Queue= Field(default_factory=Queue)
    final_answer    :Queue= Field(default_factory=Queue)
    thinking        :Queue= Field(default_factory=Queue)
    log             :Queue= Field(default_factory=Queue)
    tool_rtn_data   :Queue= Field(default_factory=Queue)

    # 开启“任意类型”支持
    model_config = ConfigDict(arbitrary_types_allowed=True)

class Query_Agent_Context(BaseModel):
    custom_data_dict    : Dict[str, Any] = Field(default_factory=dict)    # 用于存放agent调用方的自定义数据
    # template_filename   : str = ''
    # shared_filename     : str = ''

if __name__ == "__main__":
    q = Agent_Stream_Queues()
    q.output.put('hello')
    res = q.output.get()
    print(res)