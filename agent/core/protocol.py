from typing import List, Dict, Any, Type
from pydantic import BaseModel, Field, ConfigDict
from queue import Queue

class Agent_Status(BaseModel):
    started         :bool = False

    canceling       :bool = False
    canceled        :bool = False

    # paused      :bool = False     # pause似乎不需要，cancel机制即可

    finished        :bool = False
    task_success    :bool = False   #任务是否有效完成

class Agent_Stream_Queues(BaseModel):
    output          :Queue= Field(default_factory=Queue)
    final_answer    :Queue= Field(default_factory=Queue)
    thinking        :Queue= Field(default_factory=Queue)
    log             :Queue= Field(default_factory=Queue)
    tool_rtn_data   :Queue= Field(default_factory=Queue)

    # 开启“任意类型”支持
    model_config = ConfigDict(arbitrary_types_allowed=True)

class Query_Agent_Context(BaseModel):
    template_filename   : str = ''
    shared_filename     : str = ''

if __name__ == "__main__":
    q = Agent_Stream_Queues()
    q.output.put('hello')
    res = q.output.get()
    print(res)