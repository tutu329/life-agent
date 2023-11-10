
yy=44
class my_class():
    def __init__(self):
        self.z = 22

    def func(self):
        yy=3
        def _func():
            print(self.z)
            self.z += 1
            print(self.z)

        _func()

def main():
    mc = my_class()
    mc.func()

    # y=2
    # with open('my.txt', 'w') as f:
    #     y += 1
    #     print(y)

from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class One_Chat():
    chat: Tuple=('', '')

@dataclass
class Session_Data():
    user_name: str = ''
    user_passwd: str = ''
    ip: str = ''
    chat_history: List[One_Chat] = field(default_factory=list)

def main2():
    a = Session_Data()
    print(a)

def main1():
    import gradio as gr
    def echo(text, request: gr.Request):
        if request:
            print("Request headers dictionary:", request.headers)
            print("IP address:", request.client.host)
            print("Query parameters:", dict(request.query_params))
        return request.headers
        # return text

    io = gr.Interface(echo, "textbox", "textbox").launch()


if __name__ == '__main__':
    main1()