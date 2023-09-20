from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, TextStreamer, TextIteratorStreamer, StoppingCriteria, StoppingCriteriaList
from threading import Thread
import torch

class KeywordsStoppingCriteria(StoppingCriteria):
    def __init__(self, keywords_ids:list):
        self.keywords = keywords_ids

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        if input_ids[0][-1] in self.keywords:
            return True
        return False

    @classmethod
    def get_stop_criteria(cls, in_tok, in_stop_list):
        stop_words = in_stop_list
        if in_stop_list is not None:
            stop_ids = [in_tok.encode(w)[0] for w in stop_words]
            stop_criteria = KeywordsStoppingCriteria(stop_ids)
            return StoppingCriteriaList([stop_criteria])
        else:
            return None

class wizardcoder_wrapper_for_open_interpreter():
    def __init__(self):
        self.model_name_or_path = ''
        self.model = None
        self.tokenizer = None
        self.task = None

    def init(self, in_model_path):
        # self.model_name_or_path = "C:/Users/tutu/models/WizardCoder-Python-34B-V1.0-GPTQ"
        self.model_name_or_path = in_model_path
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name_or_path, device_map="auto", trust_remote_code=False, revision="main")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name_or_path, use_fast=True)

    def generate_for_open_interpreter(self, prompt, stream, temperature, max_tokens, stop=None):
        input_ids = self.tokenizer(prompt, return_tensors='pt').input_ids.cuda()
        streamer = TextIteratorStreamer(self.tokenizer)

        # stop_words = stop
        # stop_ids = [self.tokenizer.encode(w)[0] for w in stop_words]
        # stop_criteria = KeywordsStoppingCriteria(stop_ids)
        stop_criteria = KeywordsStoppingCriteria.get_stop_criteria(self.tokenizer, stop)

        generation_kwargs = dict(
            inputs=input_ids,
            streamer=streamer,
            do_sample=True,

            stopping_criteria=stop_criteria,

            temperature=temperature,
            max_new_tokens=max_tokens,
        )
        self.task = Thread(target=self.model.generate, kwargs=generation_kwargs)
        self.task.start()

        return streamer

    def get_instance_for_open_interpreter(self):
        return self.generate



# def generate_func_for_open_interpreter(prompt, stream, temperature, stop, max_tokens):
#
#     response = self.llama_instance(
#         prompt,
#         stream=True,
#         temperature=self.temperature,
#         stop=["</s>"],
#         max_tokens=750  # context window is set to 1800, messages are trimmed to 1000... 700 seems nice
#     )
#     pass
#
# def get_instance_for_open_interpreter():
#
#     return generate_func_for_open_interpreter


def main2():
    llm = wizardcoder_wrapper_for_open_interpreter()
    llm.init(in_model_path="C:/Users/tutu/models/WizardCoder-Python-34B-V1.0-GPTQ")
    while True:
        question = input('user: ')
        res = llm.generate_for_open_interpreter(
            prompt=question,
            stream=True,
            temperature=0.9,
            # stop=None,
            stop=["</s>"],
            max_tokens=512,
        )
        for chunk in res:
            print(chunk, end='', flush=True)
        print()

def main():
    # CUDA_VISIBLE_DEVICES=1,2,3,4 python wizardcoder_demo.py \
    #    --base_model "WizardLM/WizardCoder-Python-34B-V1.0" \
    #    --n_gpus 4

    model_name_or_path = "C:/Users/tutu/models/WizardCoder-Python-34B-V1.0-GPTQ"
    # To use a different branch, change revision
    # For example: revision="main"
    model = AutoModelForCausalLM.from_pretrained(model_name_or_path,
                                                 device_map="auto",
                                                 trust_remote_code=False,
                                                 revision="main")

    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True)




    prompt = "写一首爱情诗"
    # prompt = "Tell me about AI"






    # print("\n\n*** Generate:")
    #
    # input_ids = tokenizer(prompt_template, return_tensors='pt').input_ids.cuda()
    # output = model.generate(inputs=input_ids, temperature=0.7, do_sample=True, top_p=0.95, top_k=40, max_new_tokens=512)
    # print(tokenizer.decode(output[0]))

    # Inference can also be done using transformers' pipeline

    # print("*** Pipeline:")
    # # streamer = TextStreamer(tokenizer)
    # pipe = pipeline(
    #     "text-generation",
    #     model=model,
    #     streamer=streamer,
    #     tokenizer=tokenizer,
    #     max_new_tokens=2048,
    #     do_sample=True,
    #     temperature=0.7,
    #     top_p=0.95,
    #     top_k=40,
    #     repetition_penalty=1.1
    # )


    while True:
        # prompt = input('user: ')
        # prompt_template = f'''Below is an instruction that describes a task. Write a response that appropriately completes the request.
        #
        # ### Instruction:
        # {prompt}
        #
        # ### Response:
        #
        # '''
        #
        # print(pipe(prompt_template)[0]['generated_text'])


        prompt = input('user: ')
        prompt_template = f'''Below is an instruction that describes a task. Write a response that appropriately completes the request.
    
        ### Instruction:
        {prompt}
    
        ### Response:
    
        '''
        input_ids = tokenizer(prompt_template, return_tensors='pt').input_ids.cuda()
        streamer = TextIteratorStreamer(tokenizer)

        generation_kwargs = dict(inputs=input_ids, streamer=streamer, max_new_tokens=512)
        thread = Thread(target=model.generate, kwargs=generation_kwargs)
        thread.start()
        generated_text = ""
        for new_text in streamer:
            print(new_text, end='', flush=True)
            generated_text += new_text
        # generated_text


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


    # from transformers import pipeline
    # from torch.utils.data import Dataset
    # from tqdm.auto import tqdm
    #
    # pipe = pipeline("text-classification", device=0)
    #
    #
    # class MyDataset(Dataset):
    #     def __len__(self):
    #         return 5000
    #
    #     def __getitem__(self, i):
    #         return "This is a test"
    #
    #
    # dataset = MyDataset()
    #
    # for batch_size in [1, 8, 64, 256]:
    #     print("-" * 30)
    #     print(f"Streaming batch_size={batch_size}")
    #     for out in tqdm(pipe(dataset, batch_size=batch_size), total=len(dataset)):
    #         pass

if __name__ == "__main__" :
    main2()
