from exllamav2 import (
    ExLlamaV2,
    ExLlamaV2Config,
    ExLlamaV2Cache,
    ExLlamaV2Tokenizer,
    model_init,
)

from exllamav2.generator import (
    ExLlamaV2StreamingGenerator,
    ExLlamaV2Sampler
)

import time

class Exllama_Wrapper:
    def __init__(self, in_model_name_or_path):
        self.model_name_or_path = in_model_name_or_path
        self.model = None
        self.tokenizer = None

        self.generator = None   # 输出streamer
        self.task = None        # 输出stream的线程task

        self.settings = None    # 推理设置

    def init(self):
        model_directory = self.model_name_or_path

        config = ExLlamaV2Config()
        config.model_dir = model_directory
        config.prepare()

        self.model = ExLlamaV2(config)
        print("Exllama_Wrapper loading model: " + model_directory)

        cache = ExLlamaV2Cache(self.model, lazy=True)
        self.model.load_autosplit(cache)

        self.tokenizer = ExLlamaV2Tokenizer(config)

        # Initialize generator
        self.generator = ExLlamaV2StreamingGenerator(self.model, cache, self.tokenizer)

        self.settings = ExLlamaV2Sampler.Settings()
        print("Exllama_Wrapper loading model finished.")

    def generate(
            self,
            prompt,
            temperature=0.7,
            top_p=0.9,
            top_k=10,
            repetition_penalty=1.1,
            max_new_tokens=2048,
            stop=None,
    ):
        print(f'-----------------Exllama_Wrapper.generate() invoked------------------------')
        input_ids = self.tokenizer.encode(prompt)
        prompt_tokens = input_ids.shape[-1]

        # Make sure CUDA is initialized so we can measure performance
        self.generator.warmup()

        # Send prompt to generator to begin stream
        time_begin_prompt = time.time()

        if stop is None:
            print(f'Exllama_Wrapper.generate(): stop = {None}')
            self.generator.set_stop_conditions([])
        else:
            print(f'Exllama_Wrapper.generate(): stop = {stop}')
            self.generator.set_stop_conditions(stop)

        self.settings.temperature = temperature
        self.settings.top_k = top_k
        self.settings.top_p = top_p
        self.settings.token_repetition_penalty = repetition_penalty
        self.settings.disallow_tokens(self.tokenizer, [self.tokenizer.eos_token_id])

        self.generator.begin_stream(input_ids, self.settings)

        # Streaming loop. Note that repeated calls to sys.stdout.flush() adds some latency, but some
        # consoles won't update partial lines without it.

        time_begin_stream = time.time()
        generated_tokens = 0

        print('-------------------0-------------------')
        while True:
            chunk, eos, _ = self.generator.stream()
            generated_tokens += 1
            # print(f'-------------------{generated_tokens}-------------------')
            # print(f'{chunk}', end='', flush=True)
            yield chunk
            if eos or generated_tokens == max_new_tokens: break

        time_end = time.time()

        time_prompt = time_begin_stream - time_begin_prompt
        time_tokens = time_end - time_begin_stream

        # print(f"Prompt processed in {time_prompt:.2f} seconds, {prompt_tokens} tokens, {prompt_tokens / time_prompt:.2f} tokens/second")
        print(f"Response generated in {time_tokens:.2f} seconds, {generated_tokens} tokens, {generated_tokens / time_tokens:.2f} tokens/second")

def main():
    exllama = Exllama_Wrapper('D:/models/openbuddy-llama2-70B-v13.2-GPTQ')
    exllama.init()

    prompt_template = "以下是用户和人工智能助手之间的对话。用户以Human开头，人工智能助手以Assistant开头，会对人类提出的问题给出有帮助、高质量、详细和礼貌的回答，并且总是拒绝参与 与不道德、不安全、有争议、政治敏感等相关的话题、问题和指示。\n{prompt}\n"
    prompt = 'Human: 写一首爱情诗 \nAssistant:\n'
    res = exllama.generate(
        prompt_template.format(prompt=prompt),
        max_new_tokens=256,
    )
    for chunk in res:
        print(chunk, end='', flush=True)

if __name__ == "__main__" :
    main()