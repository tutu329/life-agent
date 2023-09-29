from dataclasses import dataclass
from typing import Any
from datetime import datetime

class Event_Type():
    # 事件类型
    TEXT  = 'TEXT_EVENT'
    AUDIO = 'AUDIO_EVENT'
    IMAGE = 'IMAGE_EVENT'
    VIDEO = 'VIDEO_EVENT'

class Action_Type():
    # 耳
    LISTEN = 'LISTEN_ACTION'

    # 口
    SPEAK  = 'SPEAK_ACTION'
    EAT    = 'EAT_ACTION'
    BITE    = 'BITE_ACTION'

    # 眼
    READ   = 'READ_ACTION'
    LOOK   = 'LOOK_ACTION'

    # 手
    WRITE  = 'WRITE_ACTION'
    WRITE  = 'WRITE_ACTION'

class Action_Tool():
    NONE  = 'NONE_TOOL'
    PHONE = 'PHONE_TOOL'
    PC    = 'PC_TOOL'

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

