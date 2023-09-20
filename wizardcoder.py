from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, TextStreamer, TextIteratorStreamer, StoppingCriteria, StoppingCriteriaList
from threading import Thread
import torch

class Keywords_Stopping_Criteria(StoppingCriteria):
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
            stop_criteria = Keywords_Stopping_Criteria(stop_ids)
            return StoppingCriteriaList([stop_criteria])
        else:
            return None

class Wizardcoder_Wrapper():
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

    def generate(self, prompt, stream, temperature, max_tokens, stop=None):
        input_ids = self.tokenizer(prompt, return_tensors='pt').input_ids.cuda()
        streamer = TextIteratorStreamer(self.tokenizer)

        # stop_words = stop
        # stop_ids = [self.tokenizer.encode(w)[0] for w in stop_words]
        # stop_criteria = KeywordsStoppingCriteria(stop_ids)
        stop_criteria = Keywords_Stopping_Criteria.get_stop_criteria(self.tokenizer, stop)

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

def main():
    # CUDA_VISIBLE_DEVICES=1,2,3,4 python wizardcoder_demo.py \
    #    --base_model "WizardLM/WizardCoder-Python-34B-V1.0" \
    #    --n_gpus 4

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
    # print(pipe(prompt_template)[0]['generated_text'])

    llm = Wizardcoder_Wrapper()
    llm.init(in_model_path="C:/Users/tutu/models/WizardCoder-Python-34B-V1.0-GPTQ")
    while True:
        question = input('user: ')
        prompt_template = f'''Below is an instruction that describes a task. Write a response that appropriately completes the request.
        ### Instruction:
        {question}
        ### Response:
        '''
        res = llm.generate(
            prompt=prompt_template,
            stream=True,
            temperature=0.7,
            # stop=None,
            stop=["</s>"],
            max_tokens=512,
        )
        for chunk in res:
            print(chunk, end='', flush=True)
        print()

if __name__ == "__main__" :
    main()

# https://blog.csdn.net/weixin_44878336/article/details/124894210
