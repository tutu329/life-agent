from transformers import AutoTokenizer, TextGenerationPipeline
from auto_gptq import AutoGPTQForCausalLM, BaseQuantizeConfig
import logging

# 1、修改原有模型文件夹中的modeling_qwen.py
# =====================把modeling_qwen.py中的apply_rotary_pos_emb（）改为==================================================
# def apply_rotary_pos_emb(t, freqs):
#     cos, sin = freqs
#     cos = cos.to(t.device)
#     sin = sin.to(t.device)
#     if apply_rotary_emb_func is not None and t.is_cuda:
#         t_ = t.float()
#         cos = cos.squeeze(0).squeeze(1)[:, : cos.shape[-1] // 2]
#         sin = sin.squeeze(0).squeeze(1)[:, : sin.shape[-1] // 2]
#         output = apply_rotary_emb_func(t_, cos, sin).type_as(t)
#         return output
#     else:
#         rot_dim = freqs[0].shape[-1]
#         cos, sin = freqs
#         cos = cos.to(t.device)
#         sin = sin.to(t.device)
#         t_, t_pass_ = t[..., :rot_dim], t[..., rot_dim:]
#         t_ = t_.float()
#         t_pass_ = t_pass_.float()
#         t_ = (t_ * cos) + (rotate_half(t) * sin)
#         return torch.cat((t_, t_pass_), dim=-1).type_as(t)
# =====================然后运行即可成功将模型量化为gptq======================================================================
# 2、生成safetensors文件，改名为model.safetensors，其他文件都删除。
# 3、将其他gptq中的qwen文件copy过来。即可运行

import torch
device=torch.device("cpu")

logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S"
)

pretrained_model_dir = "D:/models/Qwen-14B-Chat"
# pretrained_model_dir = "facebook/opt-125m"
quantized_model_dir = "D:/models/Qwen-72B-Chat-gptq"
# quantized_model_dir = "opt-125m-4bit"

tokenizer = AutoTokenizer.from_pretrained(pretrained_model_dir, use_fast=True, trust_remote_code=True)
examples = [
    tokenizer(
        "auto-gptq is an easy-to-use model quantization library with user-friendly apis, based on GPTQ algorithm."
    )
]

quantize_config = BaseQuantizeConfig(
    bits=4,  # quantize model to 4-bit
    group_size=128,  # it is recommended to set the value to 128
    desc_act=False,  # set to False can significantly speed up inference but the perplexity may slightly bad
)

# load un-quantized model, by default, the model will always be loaded into CPU memory
model = AutoGPTQForCausalLM.from_pretrained(pretrained_model_dir, quantize_config, low_cpu_mem_usage=True, trust_remote_code=True, device_map='auto')

# quantize model, the examples should be list of dict whose keys can only be "input_ids" and "attention_mask"
model.quantize(examples)

# save quantized model
model.save_quantized(quantized_model_dir)

# save quantized model using safetensors
model.save_quantized(quantized_model_dir, use_safetensors=True)

# push quantized model to Hugging Face Hub.
# to use use_auth_token=True, Login first via huggingface-cli login.
# or pass explcit token with: use_auth_token="hf_xxxxxxx"
# (uncomment the following three lines to enable this feature)
# repo_id = f"YourUserName/{quantized_model_dir}"
# commit_message = f"AutoGPTQ model for {pretrained_model_dir}: {quantize_config.bits}bits, gr{quantize_config.group_size}, desc_act={quantize_config.desc_act}"
# model.push_to_hub(repo_id, commit_message=commit_message, use_auth_token=True)

# alternatively you can save and push at the same time
# (uncomment the following three lines to enable this feature)
# repo_id = f"YourUserName/{quantized_model_dir}"
# commit_message = f"AutoGPTQ model for {pretrained_model_dir}: {quantize_config.bits}bits, gr{quantize_config.group_size}, desc_act={quantize_config.desc_act}"
# model.push_to_hub(repo_id, save_dir=quantized_model_dir, use_safetensors=True, commit_message=commit_message, use_auth_token=True)




# load quantized model to the first GPU
# model = AutoGPTQForCausalLM.from_quantized(quantized_model_dir, device="cuda:0")

# download quantized model from Hugging Face Hub and load to the first GPU
# model = AutoGPTQForCausalLM.from_quantized(repo_id, device="cuda:0", use_safetensors=True, use_triton=False)

# inference with model.generate
# print(tokenizer.decode(model.generate(**tokenizer("auto_gptq is", return_tensors="pt").to(model.device))[0]))

# or you can also use pipeline
# pipeline = TextGenerationPipeline(model=model, tokenizer=tokenizer)
# print(pipeline("auto-gptq is")[0]["generated_text"])cls