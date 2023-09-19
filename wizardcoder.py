from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, TextStreamer, TextIteratorStreamer

model_name_or_path = "C:/Users/tutu/models/WizardCoder-Python-34B-V1.0-GPTQ"
# To use a different branch, change revision
# For example: revision="main"
model = AutoModelForCausalLM.from_pretrained(model_name_or_path,
                                             device_map="auto",
                                             trust_remote_code=False,
                                             revision="main")

tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True)

prompt = "Tell me about AI"
prompt_template=f'''Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{prompt}

### Response:

'''

# print("\n\n*** Generate:")
#
# input_ids = tokenizer(prompt_template, return_tensors='pt').input_ids.cuda()
# output = model.generate(inputs=input_ids, temperature=0.7, do_sample=True, top_p=0.95, top_k=40, max_new_tokens=512)
# print(tokenizer.decode(output[0]))

# Inference can also be done using transformers' pipeline

print("*** Pipeline:")
# streamer = TextIteratorStreamer(tokenizer)
streamer = TextStreamer(tokenizer)
pipe = pipeline(
    "text-generation",
    model=model,
    streamer=streamer,
    tokenizer=tokenizer,
    max_new_tokens=512,
    do_sample=True,
    temperature=0.7,
    top_p=0.95,
    top_k=40,
    repetition_penalty=1.1
)

print(pipe(prompt_template)[0]['generated_text'])



# streamer = TextIteratorStreamer(tok)
#
# # Run the generation in a separate thread, so that we can fetch the generated text in a non-blocking way.
# generation_kwargs = dict(inputs, streamer=streamer, max_new_tokens=20)
# thread = Thread(target=model.generate, kwargs=generation_kwargs)
# thread.start()
# generated_text = ""
# for new_text in streamer:
#     generated_text += new_text
# generated_text
