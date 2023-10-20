from transformers import FuyuForCausalLM, AutoTokenizer, FuyuProcessor, FuyuImageProcessor
from PIL import Image
import torch

# load model, tokenizer, and processor
pretrained_path = "D:/models/fuyu-8b"
tokenizer = AutoTokenizer.from_pretrained(pretrained_path)

image_processor = FuyuImageProcessor()
processor = FuyuProcessor(image_processor=image_processor, tokenizer=tokenizer)

# model = FuyuForCausalLM.from_pretrained(pretrained_path, device_map="auto")
# torch_dtype=torch.float16 可以让显存使用控制在22G内
model = FuyuForCausalLM.from_pretrained(pretrained_path, device_map="cuda:0",  torch_dtype=torch.float16)

# test inference
# text_prompt = "Generate a coco-style caption.\n"
# image_path = "bus.png"  # https://huggingface.co/adept-hf-collab/fuyu-8b/blob/main/bus.png
# image_pil = Image.open(image_path)
#
# model_inputs = processor(text=text_prompt, images=[image_pil], device="cuda:0")
# for k, v in model_inputs.items():
#     model_inputs[k] = v.to("cuda:0")
#
# generation_output = model.generate(**model_inputs, max_new_tokens=7, pad_token_id=tokenizer.eos_token_id)
# generation_text = processor.batch_decode(generation_output[:, -7:], skip_special_tokens=True)
# assert generation_text == ['A bus parked on the side of a road.']




text_prompt = "What color is the bus?\n"
image_path = "bus.png"  # https://huggingface.co/adept-hf-collab/fuyu-8b/blob/main/bus.png
image_pil = Image.open(image_path)

model_inputs = processor(text=text_prompt, images=[image_pil], device="cuda:0")
for k, v in model_inputs.items():
    model_inputs[k] = v.to("cuda:0")

generation_output = model.generate(**model_inputs, max_new_tokens=6, pad_token_id=tokenizer.eos_token_id)
generation_text = processor.batch_decode(generation_output[:, -6:], skip_special_tokens=True)
# assert generation_text == ["The bus is blue.\n"]
print(generation_text)


text_prompt = "What is the lowest life expectancy at birth of male?\n"
image_path = "chart.png"  # https://huggingface.co/adept-hf-collab/fuyu-8b/blob/main/chart.png
image_pil = Image.open(image_path)

model_inputs = processor(text=text_prompt, images=[image_pil], device="cuda:0")
for k, v in model_inputs.items():
    model_inputs[k] = v.to("cuda:0")

generation_output = model.generate(**model_inputs, max_new_tokens=16, pad_token_id=tokenizer.eos_token_id)
generation_text = processor.batch_decode(generation_output[:, -16:], skip_special_tokens=True)
print(generation_text)
# assert generation_text == ["The life expectancy at birth of males in 2018 is 80.7.\n"]

