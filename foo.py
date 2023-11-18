
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

def p2p_speed():
    import torch
    import numpy as np

    device = torch.device("cuda")
    print(f'torch version: {torch.__version__}')
    print(f'torch.cuda.is_available: {torch.cuda.is_available()}')
    print(f'device: {device}')
    
    print(f'torch.cuda.device(0): {torch.cuda.device(0)}')
    print(f'torch.cuda.device(1): {torch.cuda.device(1)}')

    n_gpus = 2
    data_size = 1024 * 1024 * 1024  # 1 GB

    speed_matrix = np.zeros((n_gpus, n_gpus))

    for i in range(n_gpus):
        for j in range(i + 1, n_gpus):
            print(f"Testing communication between GPU {i} and GPU {j}...")
            with torch.cuda.device(i):
                data = torch.randn(data_size, device=device)
                torch.cuda.synchronize()
            with torch.cuda.device(j):
                result = torch.randn(data_size, device=device)
                torch.cuda.synchronize()
            with torch.cuda.device(i):
                start = torch.cuda.Event(enable_timing=True)
                end = torch.cuda.Event(enable_timing=True)
                start.record()
                result.copy_(data)
                end.record()
                torch.cuda.synchronize()
                elapsed_time_ms = start.elapsed_time(end)
            transfer_rate = data_size / elapsed_time_ms * 1000 * 8 / 1e9
            speed_matrix[i][j] = transfer_rate
            speed_matrix[j][i] = transfer_rate

    print(speed_matrix)

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
    # main1()
    p2p_speed()