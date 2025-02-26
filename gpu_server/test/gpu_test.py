# 需安装最新openai库

import time
from openai import OpenAI
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import uuid

g_result_dict = {
    # 'id_str': 'some_response',
}

def _single_thread_test(oai, prompt, max_tokens=100):
    start_time = time.perf_counter()
    # print(f'start_time: "{start_time}"')
    full_string = ''

    id = str(uuid.uuid4())

    try:
        model_id = oai.models.list().data[0].id
        # Create the completion with streaming
        response = oai.chat.completions.create(
            model=model_id,
            messages = [{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )

        first_token_time = None
        started = False
        tokens_received = 0
        token_start_time = None

        # Iterate over the streaming response
        for chunk in response:
            if hasattr(chunk, 'usage') and chunk.usage is not None:
                # self.usage['prompt_tokens'] = chunk.usage.prompt_tokens
                # self.usage['total_tokens'] = chunk.usage.total_tokens
                tokens_received = chunk.usage.completion_tokens
                # print(chunk.usage)
                # print(f'【prompt: {chunk.usage.prompt_tokens}】')
                # print(f'【completion: {chunk.usage.completion_tokens}】')
                # print(f'【total_tokens: {chunk.usage.total_tokens}】')

            if chunk.choices and hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
                delta = chunk.choices[0].delta.content
                full_string += delta
                # print(delta, end='', flush=True)
                if not started:
                    started = True
                    first_token_time = time.perf_counter()
                    token_start_time = first_token_time
                    # print(f'token_start_time: "{token_start_time}"')

        # print(f'【usage: "{chunk.usage}"】')
        end_time = time.perf_counter()
        # print(f'end_time: "{end_time}"')

        if first_token_time is None:
            # No tokens received
            first_token_latency = None
            avg_output_speed = None
        else:
            first_token_latency = first_token_time - start_time
            # print(f'first_token_latency: "{first_token_latency}"')
            output_duration = end_time - token_start_time
            # print(f'output_duration: "{output_duration}"')
            avg_output_speed = tokens_received / output_duration if output_duration > 0 else None

        full_string = ' '.join(full_string.split('\n'))
        g_result_dict[id] = full_string
        # print(f'LLM回复({len(full_string):5d}): {full_string[:50]}...')

        return first_token_latency, avg_output_speed, tokens_received, output_duration
    except Exception as e:
        print(f"Error in single_thread_test: {e}")
        return None, None, 0

def _concurrent_test(oai, prompt, num_concurrent=10, max_tokens=4096):
    latencies = []
    speeds = []
    tokens_list = []
    output_duration_list = []

    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(_single_thread_test, oai, prompt, max_tokens) for _ in range(num_concurrent)]

        for future in as_completed(futures):
            latency, speed, tokens_received, output_duration = future.result()
            if latency is not None:
                latencies.append(latency)
            if speed is not None:
                speeds.append(speed)
            tokens_list.append(tokens_received)
            output_duration_list.append(output_duration)

    end_time = time.perf_counter()

    total_tokens = sum(tokens_list)
    total_time = end_time - start_time
    total_throughput = total_tokens / total_time if total_time > 0 else None

    if latencies:
        first_token_latency_max = max(latencies)
        first_token_latency_min = min(latencies)
        first_token_latency_avg = sum(latencies) / len(latencies)
    else:
        first_token_latency_max = None
        first_token_latency_min = None
        first_token_latency_avg = None

    if speeds:
        avg_output_speed_max = max(speeds)
        avg_output_speed_min = min(speeds)
        avg_output_speed_avg = sum(speeds) / len(speeds)
    else:
        avg_output_speed_max = None
        avg_output_speed_min = None
        avg_output_speed_avg = None

    if output_duration_list:
        task_time_max = max(output_duration_list)
        task_time_min = min(output_duration_list)
        task_time_avg = sum(output_duration_list) / len(output_duration_list)
    else:
        task_time_max = None
        task_time_min = None
        task_time_avg = None

    return {
        'total_throughput': total_throughput,
        'total_tokens': total_tokens,
        'total_time': total_time,
        'task_time':{
            'max': task_time_max,
            'min': task_time_min,
            'avg': task_time_avg,
        },
        'first_token_latency': {
            'max': first_token_latency_max,
            'min': first_token_latency_min,
            'avg': first_token_latency_avg,
        },
        'average_output_speed': {
            'max': avg_output_speed_max,
            'min': avg_output_speed_min,
            'avg': avg_output_speed_avg,
        }
    }

def gpu_test(
    prompt='写一首长诗',
    num_concurrent=100,
    url='https://powerai.cc:8001/v1',
    max_tokens=4096,
    show_result=False,
    test_single_thread=True,
):

    oai = OpenAI(
        api_key='empty',
        base_url=url,
    )

    if test_single_thread:
        print("\n---------启动单线程测试---------")
        latency, speed, tokens_received, output_duration = _single_thread_test(oai, prompt, max_tokens)
        print(f"首字延时: \t{latency:.4f} \tseconds")
        print(f"回复速度: \t{speed:.2f} \ttokens/second")
        print(f"回复数量: \t{tokens_received} \ttokens")
        print(f"回复时间: \t{output_duration:.1f} \tseconds")

    print(f"---------启动多线程测试({num_concurrent}线程)---------")
    results = _concurrent_test(oai, prompt, num_concurrent, max_tokens)
    print(f"总吞吐量: \t{results['total_throughput']:.2f} \ttokens/second")
    print(f"总回复量: \t{results['total_tokens']:.2f} \ttokens")
    print(f"回复总时: \t{results['total_time']:.2f} \tseconds")

    print(f"子项时间(max): \t{results['task_time']['max']:.2f} \tseconds")
    print(f"子项时间(min): \t{results['task_time']['min']:.2f} \tseconds")
    print(f"子项时间(avg): \t{results['task_time']['avg']:.2f} \tseconds")

    print(f"首字延时(max): \t{results['first_token_latency']['max']:.4f} \tseconds")
    print(f"首字延时(min): \t{results['first_token_latency']['min']:.4f} \tseconds")
    print(f"首字延时(avg): \t{results['first_token_latency']['avg']:.4f} \tseconds")
    print(f"回复速度(max): \t{results['average_output_speed']['max']:.2f} \ttokens/second")
    print(f"回复速度(min): \t{results['average_output_speed']['min']:.2f} \ttokens/second")
    print(f"回复速度(avg): \t{results['average_output_speed']['avg']:.2f} \ttokens/second")

    if show_result:
        print("\n---------测试回复结果汇编---------")
        i = 0
        for k,v in g_result_dict.items():
            i += 1
            print(f'LLM回复[{i:4d}]({len(v):5d}): {v[:50]}...')

def main():
    url = 'https://powerai.cc:8001/v1'
    prompt = '写一首长诗'
    test_nums = [10, 20, 30, 40, 50, 100]
    # test_nums = [10]
    for num in test_nums:
        gpu_test(
            prompt=prompt,
            num_concurrent=num,
            url=url,
            max_tokens=4096,
            show_result=False,
            test_single_thread=(num==test_nums[0]),
        )

if __name__ == '__main__':
    main()
