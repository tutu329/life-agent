from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional

from agent.core.protocol import Query_Agent_Context
from agent.core.agent_config import Agent_Config
from utils.task import Status

from datetime import datetime
import copy, threading
from uuid import uuid4

from config import dgreen

class Tool_Info(BaseModel):
    tool_task_id        : str                       # 工具所执行任务的id
    tool_task_status    : Status = Status.Created   # 工具所执行任务的Status：Created、Initializing、Initialized、Running、Cancelling、Cancelled、Completed

class Data_Set_Info(BaseModel):
    data_set_content_url    : str                           # 数据集的完整内容的url（带过期签名的对象存储 URL，通常为pyarrow的url）
    data_schema             : str                           # 如"user_id:int, date:date, kWh:float"
    rows                    : int                           # 数据集的总行数
    cols                    : int                           # 数据集的总列数
    sample                  : Optional[list] = None         # 可选：样例数据，如20行以内的head或tail
    expires_at              : Optional[datetime] = None     # 可选：指向文件的过期时间，用于前端提示刷新 URL

    # 开启“任意类型”支持
    # model_config = ConfigDict(arbitrary_types_allowed=True)

class Tool_Context(BaseModel):
    """
    Tool_Context类，用于agent调用多个tool时，tool之间的数据上下文交互：
        如agent调用数据库tool后，返回的大量数据，存放于Tool_Context中，给下一个tool用，而不用流过LLM。
    """
    tool_info       : Tool_Info                         # tool的id和所执行任务的status
    data_set_info   : Optional[Data_Set_Info] = None    # 可选：数据集信息（包括url）

    # 开启“任意类型”支持
    # model_config = ConfigDict(arbitrary_types_allowed=True)

class Registered_Remote_Tool_Data(BaseModel):
    """
    Registered_Remote_Tool_Data类，注册remote_tool时用的参数
    """
    name            : str                               # 如："Remote_Folder_Tool"
    description     : str                               # 如："返回远程服务器上指定文件夹下所有文件和文件夹的名字信息。"
    parameters      : List[Dict[str, str]]              # 要求为：[{"name": "para1", "type": "string", "description": "本参数为文件夹所在的路径", "required": "True"}]
    endpoint_url    : str                               # 如："http://localhost:{Port.remote_tool_fastapi_server}/Folder_Tool"
    method          : str = "POST"                      # 如：'POST'、'GET'
    timeout         : float = 10.0                      # 如：10、15
    headers         : Optional[Dict[str, str]] = None

class Tool_Call_Paras(BaseModel):
    """
    Tool_Call_Paras类，agent调用tool时，传递给tool的参数
    """
    callback_tool_paras_dict    :Optional[Dict[str, Any]] = None# 如：{'file_path': './', 'xx':'xx', ...}
    callback_agent_config       :Agent_Config                   # base_url、api_key、model_id、temperature等
    callback_top_agent_id       :str                            # 顶层的agent_id，主要用于多层agents系统中，让top_agent_id<-->connection，而与下层agent_id无关
    callback_agent_id           :str                            # 如：str(uuid4())
    callback_last_tool_ctx      :Optional[Tool_Context] = None  # 上一个tool调用后的上下文结果
    callback_client_ctx         :Optional[Query_Agent_Context] = None  # client发过来的context
    callback_father_agent_exp   :str                            # 如："搜索远程文件夹的经验是，如果失败可能是..."

    callback_tool_call_id       :str                            # 每调用一次tool的唯一ID, 主要用于resource_id

    # 开启“任意类型”支持
    # model_config = ConfigDict(arbitrary_types_allowed=True)


class Action_Result(BaseModel):
    result          :str
    data_set_info   :Optional[Data_Set_Info] = None

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
        data_set_info:Data_Set_Info=None
):
    # 更新dataset信息，同时status改为completed
    with _TOOL_CTX_STORE_LOCK:
        tool_context = Tool_Context(
            tool_info = Tool_Info(tool_task_id=tool_ctx.tool_info.tool_task_id, tool_task_status=Status.Completed),
            data_set_info = data_set_info
        )
        _TOOL_CTX_STORE[tool_ctx.tool_info.tool_task_id] = copy.deepcopy(tool_context)

        dgreen(f'------------------updated tool_context-------------------\n{tool_context}')
        dgreen(f'------------------/updated tool_context-------------------')

