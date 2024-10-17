import time
import openai
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

def single_thread_test(prompt, max_tokens=100):
    start_time = time.perf_counter()

    try:
        # Create the completion with streaming
        response = openai.chat.completions.create(
            model="qwen72",
            messages = [{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            stream=True
        )

        first_token_time = None
        tokens_received = 0
        token_start_time = None

        # Iterate over the streaming response
        for chunk in response:
            if 'choices' in chunk:
                choices = chunk['choices']
                if choices and 'delta' in choices[0]:
                    delta = choices[0]['delta']
                    if 'content' in delta:
                        print(delta, end='', flush=True)
                        # Token received
                        tokens_received += 1
                        if tokens_received == 1:
                            # First token received
                            first_token_time = time.perf_counter()
                            token_start_time = first_token_time
        end_time = time.perf_counter()

        if first_token_time is None:
            # No tokens received
            first_token_latency = None
            avg_output_speed = None
        else:
            first_token_latency = first_token_time - start_time
            output_duration = end_time - token_start_time
            avg_output_speed = tokens_received / output_duration if output_duration > 0 else None

        return first_token_latency, avg_output_speed, tokens_received
    except Exception as e:
        print(f"Error in single_thread_test: {e}")
        return None, None, 0

def concurrent_test(prompt, num_concurrent=10, max_tokens=100):
    latencies = []
    speeds = []
    tokens_list = []

    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(single_thread_test, prompt, max_tokens) for _ in range(num_concurrent)]

        for future in as_completed(futures):
            latency, speed, tokens_received = future.result()
            if latency is not None:
                latencies.append(latency)
            if speed is not None:
                speeds.append(speed)
            tokens_list.append(tokens_received)

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

    return {
        'total_throughput': total_throughput,
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

def main():
    parser = argparse.ArgumentParser(description="GPU性能测试.")
    parser.add_argument('--prompt', type=str, default='写一首长诗', help='Prompt to send to the LLM')
    parser.add_argument('--max_tokens', type=int, default=100, help='Maximum number of tokens to generate')
    parser.add_argument('--num_concurrent', type=int, default=10, help='Number of concurrent accesses')
    parser.add_argument('--api_base', type=str, default='https://powerai.cc:8001/v1', help='Base URL for the OpenAI API')
    parser.add_argument('--api_key', type=str, default='empty', help='API key for OpenAI API')

    args = parser.parse_args()

    if args.api_base:
        openai.api_base = args.api_base
    if args.api_key:
        openai.api_key = args.api_key
    else:
        openai.api_key = 'EMPTY'  # Use a default or empty API key for local deployment

    print("Starting single-threaded test...")
    latency, speed, tokens_received = single_thread_test(args.prompt, args.max_tokens)
    print(f"Single-threaded test results:")
    print(f"First token latency: {latency:.4f} seconds")
    print(f"Average output speed: {speed:.2f} tokens/second")
    print(f"Total tokens received: {tokens_received}")

    print("\nStarting concurrent test...")
    results = concurrent_test(args.prompt, args.num_concurrent, args.max_tokens)
    print(f"Concurrent test results:")
    print(f"Total throughput: {results['total_throughput']:.2f} tokens/second")
    print(f"First token latency (max): {results['first_token_latency']['max']:.4f} seconds")
    print(f"First token latency (min): {results['first_token_latency']['min']:.4f} seconds")
    print(f"First token latency (avg): {results['first_token_latency']['avg']:.4f} seconds")
    print(f"Average output speed (max): {results['average_output_speed']['max']:.2f} tokens/second")
    print(f"Average output speed (min): {results['average_output_speed']['min']:.2f} tokens/second")
    print(f"Average output speed (avg): {results['average_output_speed']['avg']:.2f} tokens/second")

if __name__ == '__main__':
    main()
