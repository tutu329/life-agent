# from transformers import AutoTokenizer
# from vllm import LLM, SamplingParams
#
# max_model_len, tp_size = 8192, 1
# model_name = "/home/tutu/models/DeepSeek-V2-Lite-Chat"
# tokenizer = AutoTokenizer.from_pretrained(model_name)
# llm = LLM(model=model_name, tensor_parallel_size=tp_size, dtype='half', max_model_len=max_model_len, trust_remote_code=True, enforce_eager=True)
# sampling_params = SamplingParams(temperature=0.3, max_tokens=256, stop_token_ids=[tokenizer.eos_token_id])
#
# messages_list = [
#     [{"role": "user", "content": "Who are you?"}],
#     [{"role": "user", "content": "Translate the following content into Chinese directly: DeepSeek-V2 adopts innovative architectures to guarantee economical training and efficient inference."}],
#     [{"role": "user", "content": "Write a piece of quicksort code in C++."}],
# ]
#
# prompt_token_ids = [tokenizer.apply_chat_template(messages, add_generation_prompt=True) for messages in messages_list]
#
# outputs = llm.generate(prompt_token_ids=prompt_token_ids, sampling_params=sampling_params)
#
# generated_text = [output.outputs[0].text for output in outputs]
# print(generated_text)

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig

model_name = "/home/tutu/models/DeepSeek-V2-Lite-Chat"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True, torch_dtype=torch.float16).cuda()
model.generation_config = GenerationConfig.from_pretrained(model_name)
model.generation_config.pad_token_id = model.generation_config.eos_token_id

messages = [
    {"role": "user", "content": "Write a piece of quicksort code in C++"}
]
input_tensor = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt")
outputs = model.generate(input_tensor.to(model.device), max_new_tokens=100)

result = tokenizer.decode(outputs[0][input_tensor.shape[1]:], skip_special_tokens=True)
print(result)
###

