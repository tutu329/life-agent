from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from redis_proxy.custom_command.protocol import Redis_Task_Type

@dataclass
class Key_Name_Space:
    Task_Register: str = "Redis_Proxy_Server_Tasks"
    # Bridge_Register: str = "Redis_Proxy_Server_Bridges"

    Commands_Register: str = 'Task_{task_id}_Commands'
    Results_Register: str = 'Task_{task_id}_Command_{command_id}_Results'


@dataclass
class Client_New_Task_Paras:    # new task是顶层命令，不适合放在custom_command下面（与自定义的功能无关）
    client_id: str = ''     # client_id由client提供，可以是str(uuid.uuid4())
    task_type: str = ''     # 见custom_command.protocol中的Redis_Task_Type
    task_id: str = ''       # task_id由client提供，可以是str(uuid.uuid4())
