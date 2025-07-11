import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from uuid import uuid4
from utils.task import Status
import threading

@dataclass
class Tool_Info:
    tool_task_id: str                           # 工具所执行任务的id
    tool_task_status: Status = Status.Created   # 工具所执行任务的status

@dataclass
class Data_Set_Info:
    data_set_content_url: str   # 数据集的完整内容的url（带过期签名的对象存储 URL，通常为pyarrow的url）
    schema: str                 # 如"user_id:int, date:date, kWh:float"
    rows: int                   # 数据集的总行数
    cols: int                   # 数据集的总列数
    sample: Optional[list] = field(default=None)            # 可选：样例数据，如20行以内的head或tail
    expires_at: Optional[datetime] = field(default=None)    # 可选：指向文件的过期时间，用于前端提示刷新 URL

@dataclass
class Tool_Context:
    """
    Tool_Context类，用于agent调用多个tool时，tool之间的数据上下文交互：
        如agent调用数据库tool后，返回的大量数据，存放于Tool_Context中，给下一个tool用，而不用流过LLM。
    """
    tool_info: Tool_Info                                            # tool的id和所执行任务的status
    # action_result: str = ''                                         # tool留给LLM的可读信息(tool_msg_for_llm)
    data_set_info: Optional[Data_Set_Info] = field(default=None)    # 可选：数据集信息（包括url）


@dataclass
class Action_Result:
    result:str
    data_set_info:Data_Set_Info = field(default=None)

_TOOL_CTX_STORE: Dict[str, Tool_Context] = {}
_TOOL_CTX_STORE_LOCK = threading.Lock()                   # 轻量串行化；高并发可换 Redis 分布式锁

def create_tool_ctx():
    """
    创建一个新的tool_ctx，返回tool_ctx（包含dataset等信息）。
    """
    tool_task_id = str(uuid4())
    tool_ctx = Tool_Context(
            tool_info=Tool_Info(tool_task_id=tool_task_id),
        )
    with _TOOL_CTX_STORE_LOCK:
        _TOOL_CTX_STORE[tool_task_id] = tool_ctx
    return tool_ctx

def get_tool_ctx(tool_task_id:str):
    """
    根据tool_task_id，返回tool_ctx（包含dataset等信息）
    """
    tool_ctx = _TOOL_CTX_STORE.get(tool_task_id)
    return tool_ctx

def update_tool_context_info(
        tool_ctx:Tool_Context,
        # action_result='',
        data_set_info:Data_Set_Info=None
):
    # 更新dataset信息，同时status改为completed
    with _TOOL_CTX_STORE_LOCK:
        tool_context = Tool_Context(
            tool_info = Tool_Info(tool_task_id=tool_ctx.tool_info.tool_task_id, tool_task_status=Status.Completed),
            # action_result = action_result,
            data_set_info = data_set_info
        )
        _TOOL_CTX_STORE[tool_ctx.tool_info.tool_task_id] = copy.deepcopy(tool_context)

        print(f'------------------updated tool_context-------------------\n{tool_context}')
        print(f'------------------/updated tool_context-------------------')
