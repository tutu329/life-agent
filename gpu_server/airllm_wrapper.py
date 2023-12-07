from airllm import AirLLMLlama2

MAX_LENGTH = 128

# could use hugging face model repo id:
# model = AirLLMLlama2("D:\models\openbuddy-llama2-70B-v13.2-GPTQ")
model = AirLLMLlama2("D:/models/Qwen-14B-Chat", layer_shards_saving_path='D:/models/Qwen-14B-Chat')
# model = AirLLMLlama2("D:/models/Qwen-14B-Chat", layer_shards_saving_path='D:/models/Qwen-14B-Chat')
# model = AirLLMLlama2("D:/models/Qwen-72B-Chat")

# or use model's local path...
# model = AirLLMLlama2("/home/ubuntu/.cache/huggingface/hub/models--garage-bAInd--Platypus2-70B-instruct/snapshots/b585e74bcaae02e52665d9ac6d23f4d0dbc81a0f")

input_text = [
    'What is the capital of United States?',
    # 'I like',
]

input_tokens = model.tokenizer(input_text,
                               return_tensors="pt",
                               return_attention_mask=False,
                               truncation=True,
                               max_length=MAX_LENGTH,
                               padding=True)

generation_output = model.generate(
    input_tokens['input_ids'].cuda(),
    max_new_tokens=20,
    use_cache=True,
    return_dict_in_generate=True)

output = model.tokenizer.decode(generation_output.sequences[0])

print(output)
