import torch
import numpy as np

def nvlink_p2p_speed(gpu_num=2):
    print(f'torch version: {torch.__version__}')
    print(f'torch.cuda.is_available: {torch.cuda.is_available()}')
    print(f'torch.device: {torch.device("cuda")}')

    device = torch.device("cuda")
    n_gpus = gpu_num
    data_size = 1024 * 1024 * 1024  # 1 GB

    speed_matrix = np.zeros((n_gpus, n_gpus))

    for i in range(n_gpus):
        for j in range(i + 1, n_gpus):
            print(f"测试 GPU {i} 和 GPU {j} 之间的通信速度...")
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

    print(f'{"":>5}', end='')
    for i in range(n_gpus):
        gpu_string = f'GPU{i:>2}'
        print(f'{gpu_string:>13}', end='')   # >为右对齐，<为左对齐，^为居中对齐
    print()

    for i in range(n_gpus):
        gpu_string = f'GPU{i:>2}'
        print(f'{gpu_string}', end='')
        for j in range(n_gpus):
            print(f'{speed_matrix[i][j]:>8.2f} GB/s', end='')
        print()

if __name__ == '__main__':
    nvlink_p2p_speed(gpu_num=2)

