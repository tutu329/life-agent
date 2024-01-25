
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

def autogptq():
    model_dir = 'D:/models/openbuddy-llama2-70B-v13.2-GPTQ'
    # model_dir = "D:/models/Qwen-72B-Chat-Int4"
    pretrained_model_dir = model_dir
    quantized_model_dir = model_dir

    from transformers import AutoTokenizer, pipeline, logging
    from auto_gptq import AutoGPTQForCausalLM, BaseQuantizeConfig
    import argparse

    model_name_or_path = model_dir
    model_basename = "openbuddy-llama2-70B-v13.2-GPTQ-4bit.act-order"

    use_triton = False

    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True, trust_remote_code=True)

    model = AutoGPTQForCausalLM.from_quantized(model_name_or_path,
                                               model_basename=model_basename,
                                               use_safetensors=True,
                                               trust_remote_code=True,
                                               # device="cuda:0",
                                               use_triton=use_triton,
                                               quantize_config=None)

    prompt = "Tell me about AI"
    prompt_template = f'''### Human: {prompt}
    ### Assistant:'''

    print("\n\n*** Generate:")

    input_ids = tokenizer(prompt_template, return_tensors='pt').input_ids.cuda()
    output = model.generate(inputs=input_ids, temperature=0.7, max_new_tokens=512)
    print(tokenizer.decode(output[0]))

    # Inference can also be done using transformers' pipeline

    # Prevent printing spurious transformers error when using pipeline with AutoGPTQ
    logging.set_verbosity(logging.CRITICAL)

    print("*** Pipeline:")
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=512,
        temperature=0.7,
        top_p=0.95,
        repetition_penalty=1.15
    )

    print(pipe(prompt_template)[0]['generated_text'])

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

def mix():
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

    model_name_or_path = "D:\models\Mixtral_34Bx2_MoE_60B-GPTQ"
    # To use a different branch, change revision
    # For example: revision="gptq-4bit-128g-actorder_True"
    model = AutoModelForCausalLM.from_pretrained(model_name_or_path,
                                                 device_map="auto",
                                                 trust_remote_code=False,
                                                 revision="main")

    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True)

    prompt = "Write a story about llamas"
    system_message = "You are a story writing assistant"
    prompt_template = f'''{prompt}
    '''

    print("\n\n*** Generate:")

    input_ids = tokenizer(prompt_template, return_tensors='pt').input_ids.cuda()
    output = model.generate(inputs=input_ids, temperature=0.7, do_sample=True, top_p=0.95, top_k=40, max_new_tokens=512)
    print(tokenizer.decode(output[0]))

    # Inference can also be done using transformers' pipeline

    print("*** Pipeline:")
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=512,
        do_sample=True,
        temperature=0.7,
        top_p=0.95,
        top_k=40,
        repetition_penalty=1.1
    )

    print(pipe(prompt_template)[0]['generated_text'])

def autogptq1():
    print("==============1================")
    model_dir = "D:\models\Mixtral_34Bx2_MoE_60B-GPTQ"
    # model_dir = "D:/models/Qwen-72B-Chat-Int4"
    pretrained_model_dir = model_dir
    quantized_model_dir = model_dir

    from transformers import AutoTokenizer, pipeline, logging, AutoModelForCausalLM
    from auto_gptq import AutoGPTQForCausalLM, BaseQuantizeConfig
    import argparse

    model_name_or_path = model_dir
    model_basename = "openbuddy-llama2-70B-v13.2-GPTQ-4bit.act-order"

    use_triton = False

    print("==============2================")
    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True, trust_remote_code=True)
    print("==============3================")

    model = AutoModelForCausalLM.from_pretrained(model_name_or_path,
                                                 device_map="auto",
                                                 trust_remote_code=False,
                                                 revision="main")

    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True)

    print("==============4================")
    prompt = "Tell me about AI"
    prompt_template = f'''### Human: {prompt}
    ### Assistant:'''

    print("\n\n*** Generate:")

    input_ids = tokenizer(prompt_template, return_tensors='pt').input_ids.cuda()
    output = model.generate(inputs=input_ids, temperature=0.7, max_new_tokens=512)
    print(tokenizer.decode(output[0]))

    # Inference can also be done using transformers' pipeline

    # Prevent printing spurious transformers error when using pipeline with AutoGPTQ
    logging.set_verbosity(logging.CRITICAL)

    print("*** Pipeline:")
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=512,
        temperature=0.7,
        top_p=0.95,
        repetition_penalty=1.15
    )

    print(pipe(prompt_template)[0]['generated_text'])

if __name__ == '__main__':
    # main1()
    # p2p_speed()
    autogptq1()
    # mix()
    # heihei