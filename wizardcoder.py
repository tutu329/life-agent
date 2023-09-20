from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, TextStreamer
from transformers import TextIteratorStreamer, StoppingCriteria, StoppingCriteriaList
from transformers.generation import GenerationConfig
from transformers import GPTQConfig
from threading import Thread
import torch
from tqdm import tqdm
import time

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

class Progress_Task(Thread):
    def __init__(self):
        super().__init__()
        self.__task = None
        self.__task_finished = False
        self.__progress = None
        self.__progress_now = 0

    def run(self):
        # print('=====================enter===============================')
        time.sleep(1)
        self.__progress = tqdm(total=100)
        while not self.__task_finished:
            time.sleep(1)
            self.__progress.update(1)
            self.__progress_now += 1
        self.__progress.update(100 - self.__progress_now)
        self.__progress.close()
        # print('=====================quit===============================')

    def set_finished(self):
        self.__task_finished = True

class Wizardcoder_Wrapper():
    def __init__(self):
        self.model_name_or_path = ''
        self.model = None
        self.tokenizer = None
        self.task = None

    # model的初始化
    def init(self, in_model_path, use_fast=True, gptq_bits=4, gptq_use_exllama=True, device_map='auto', trust_remote_code=False, revision='main'):
        print('-'*80)
        self.model_name_or_path = in_model_path
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name_or_path, use_fast=use_fast)
        quantization_config = GPTQConfig(bits=gptq_bits, disable_exllama=not gptq_use_exllama)     # 只有4bit的才可以用exllama
        print(f'设置模型路径: \t\t"{self.model_name_or_path}"', flush=True)
        print(f'设置tokenizer: \t\t"use_fast={use_fast}"', flush=True)
        print(f'设置quantization_config:"bits={gptq_bits} disable_exllama={not gptq_use_exllama}"', flush=True)
        print(f'设置model: \t\t"device_map={device_map} trust_remote_code={trust_remote_code} revision={revision}"', flush=True)

        # 读取model并显示进度条
        print('-'*80)
        p_task = Progress_Task()
        p_task.start()
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name_or_path,
            quantization_config=quantization_config,
            device_map=device_map,
            trust_remote_code=trust_remote_code,
            revision=revision)
        p_task.set_finished()
        time.sleep(1)   # 解决进度条显示问题

        self.model.generation_config = GenerationConfig.from_pretrained(self.model_name_or_path)
        self.model.generation_config.do_sample = True
        print(f'设置generation_config: \tgeneration_config={self.model.generation_config}', flush=True)
        print(f'设置其他参数: \t\t"do_sample={self.model.generation_config.do_sample}"', flush=True)
        print('-'*80)

    # model生成内容，并返回streamer迭代器
    def generate(self, message, history, temperature=0.7, max_tokens=512, stop=None):
        input_ids = self.tokenizer(message, return_tensors='pt').input_ids.cuda()
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True)

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

    # oi用的generate
    def generate_for_open_interpreter(self, prompt, stream, temperature, max_tokens, stop=None):
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

        res = {
            'choices': [
                {
                    'text': '',
                    'finish_reason': '',
                }
            ]
        }
        for chunk in streamer:
            res["choices"][0]["text"] = chunk
            yield res
        res["choices"][0]["finish_reason"] = 'stop'
        return res

    # oi用的获取instance
    def get_instance_for_open_interpreter(self, in_stream):
        res = {
            'choices':[
                {
                    'text':'',
                }
            ]
        }
        for chunk in in_stream:
            res["choices"][0]["text"] = chunk
            yield res


def main():
    # CUDA_VISIBLE_DEVICES=1,2,3,4 python wizardcoder_demo.py \
    #    --base_model "WizardLM/WizardCoder-Python-34B-V1.0" \
    #    --n_gpus 4
    llm = Wizardcoder_Wrapper()
    llm.init(in_model_path="C:/Users/tutu/models/WizardCoder-Python-34B-V1.0-GPTQ")
    while True:
        question = input('user: ')
        prompt_template = f'''Below is an instruction that describes a task. Write a response that appropriately completes the request.
        ### Instruction:
        {question}
        ### Response:
        '''
        res = llm.generate(prompt_template, [])
        for chunk in res:
            print(chunk, end='', flush=True)
        print()
        # res = llm.generate_for_open_interpreter(
        #     prompt=prompt_template,
        #     stream=True,
        #     temperature=0.7,
        #     # stop=None,
        #     stop=["</s>"],
        #     max_tokens=512,
        # )
        # for chunk in res:
        #     print(chunk["choices"][0]["text"], end='', flush=True)
        # print()




def main_gr():
    import gradio as gr

    llm = Wizardcoder_Wrapper()
    llm.init(in_model_path="C:/Users/tutu/models/WizardCoder-Python-34B-V1.0-GPTQ")
    def ask_llm(message, history):
        prompt_template = f'''Below is an instruction that describes a task. Write a response that appropriately completes the request.
        ### Instruction:
        {message}
        ### Response:
        '''
        print('==================ask_llm==================')
        # print(message, history)
        res = ''
        for ch in llm.generate(prompt_template, history, max_tokens=200):
            print(ch, end='', flush=True)
            res += ch
            yield res

    demo = gr.ChatInterface(ask_llm).queue().launch()

if __name__ == "__main__" :
    main_gr()

# https://blog.csdn.net/weixin_44878336/article/details/124894210
