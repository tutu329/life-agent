from dataclasses import dataclass
from typing import Any
from datetime import datetime


class Event_Type():
    # 事件类型
    TEXT  = 'EVENT_TEXT'
    AUDIO = 'EVENT_AUDIO'
    IMAGE = 'EVENT_IMAGE'
    VIDEO = 'EVENT_VIDEO'

class Action_Type():
    # 脑
    THINK  = 'ACTION_THINK'

    # 耳
    LISTEN = 'ACTION_LISTEN'

    # 口
    SPEAK  = 'ACTION_SPEAK'
    EAT    = 'ACTION_EAT'
    BITE   = 'ACTION_BITE'

    # 眼
    READ   = 'ACTION_READ'
    LOOK   = 'ACTION_LOOK'

    # 手
    WRITE  = 'ACTION_WRITE'

class Action_Tool():
    NONE  = 'TOOL_NONE'
    PHONE = 'TOOL_PHONE'
    PC    = 'TOOL_PC'

@dataclass
class Environment_Event:
    time    :datetime = None        # "2023-09-29 16:39:19"
    type    :str = Event_Type.TEXT  # "TEXT_EVENT"

    subject :str = 'NO_BODY'            # 我
    object  :str = 'NO_BODY'            # 你
    tool    :str = Action_Tool.NONE     # 手机
    action  :str = Action_Type.SPEAK    # 说话

    content :Any = None # "你在做什么?"

    def __str__(self):
        res = f'({self.time.strftime("%Y-%m-%d %H:%M:%S")})"{self.type}": [{self.subject}] [{self.action}] to [{self.object}] with [{self.tool}] ("{self.content}")'
        return res

# 异步的Environment类
# 功能：记录agent的所有action，是一个发布-订阅agent行为的异步消息中间件（后续可考虑跨进程，如基于redis）
# 注意：agent不知道Environment的存在，Environment
class Async_Environment():
    def __init__(self):
        self.history:list[Environment_Event] = []

    def append_event(self, in_type, in_sub, in_obj, in_action, in_tool, in_content):
        self.history.append(Environment_Event(datetime.now(), in_type, in_sub, in_obj, in_tool, in_action, in_content))

    def print_history(self):
        for item in self.history:
            print(item)


def main():
    env = Async_Environment()
    env.append_event(
        Event_Type.TEXT,
        'I',
        'YOU',
        'SPEAK',
        'PHONE',
        '你在干嘛？'
    )
    env.print_history()

if __name__ == "__main__":
    main()

