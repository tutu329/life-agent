from copy import deepcopy
import numpy as np
import os, requests
# import os, requests, torch
import matplotlib.figure as mplfigure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.colors as mplc
from matplotlib.font_manager import FontProperties
import matplotlib as mpl
from PIL import Image
from typing import Collection, Dict, List, Set, Tuple, Union, Any, Callable, Optional
import random
import re

import sys
import platform



if sys.platform.startswith('win'):      # win下用的是qwen的openai api (openai==0.28.1)
    import openai
    openai.api_base = ''
    openai.api_key = "EMPTY"
elif sys.platform.startswith('linux'):  # linux下用的是vllm的openai api (openai>1.0.0)
    from openai import OpenAI
else:
    raise Exception('无法识别的操作系统！')

class LLM_Client():
    def __init__(self, history=True, history_max_turns=50, history_clear_method='pop', temperature=0.7, url='http://127.0.0.1:8001/v1', need_print=True):
        print(f'【LLM_Client】 LLM_Client() inited.')
        if sys.platform.startswith('win'):          # win下用的是qwen的openai api
            openai.api_key = "EMPTY"
            openai.api_base = url
            self.model = 'local model'
            print(f'【LLM_Client】 os: windows. openai api for qwen used.')
            print(f'【LLM_Client】 model: {self.model}')
        elif sys.platform.startswith('linux'):      # linux下用的是vllm的openai api
            self.openai = OpenAI(
                api_key='EMPTY',
                base_url=url,
            )
            self.model = self.openai.models.list().data[0].id
            print(f'【LLM_Client】 os: linux. openai api for vllm used.')
            print(f'【LLM_Client】 model: {self.model}')
        else:
            raise Exception('无法识别的操作系统！')

        self.url = url
        self.gen = None     # 返回结果的generator
        self.response_canceled = False  # response过程是否被中断
        self.temperature = temperature
        # self.top_k = top_k  # 需要回答稳定时，可以不通过调整temperature，直接把top_k设置为1; 官方表示qwen默认的top_k为0即不考虑top_k的影响

        # 记忆相关
        self.history_list = []
        self.history = history
        self.history_max_turns = history_max_turns
        self.history_turn_num_now = 0

        self.history_clear_method = history_clear_method     # 'clear' or 'pop'

        self.question_last_turn = ''
        self.answer_last_turn = ''

        self.role_prompt = ''
        self.has_role_prompt = False

        self.external_last_history = []     # 用于存放外部格式独特的history
        self.need_print = need_print

    # 动态修改role_prompt
    # def set_role_prompt(self, in_role_prompt):
    #     if in_role_prompt=='':
    #         return
    #
    #     self.role_prompt = in_role_prompt
    #     if self.history_list!=[]:
    #         self.history_list[0] = {"role": "user", "content": self.role_prompt}
    #         self.history_list[1] = {"role": "assistant", "content": '好的，我明白了，现在就开始，我会严格按照要求来。'}
    #     else:
    #         self.history_list.append({"role": "user", "content": self.role_prompt})
    #         self.history_list.append({"role": "assistant", "content": '好的，我明白了，现在就开始，我会严格按照要求来。'})

    def set_role_prompt(self, in_role_prompt):
        if in_role_prompt!='':
            # role_prompt有内容
            self.role_prompt = in_role_prompt

            # qwen-72b和qwen-1.8b
            if sys.platform.startswith('win'):          # win下用的是qwen的openai api
                if self.has_role_prompt and len(self.history_list)>0 :
                    # 之前已经设置role_prompt
                    self.history_list[0] = {"role": "system", "content": self.role_prompt}
                else:
                    # 之前没有设置role_prompt
                    self.history_list.insert(0, {"role": "system", "content": self.role_prompt})
                    self.has_role_prompt = True
            elif sys.platform.startswith('linux'):  # linux下用的是vllm的openai api
                # 早期qwen版本或其他llm
                if self.has_role_prompt and len(self.history_list)>0 :
                    # 之前已经设置role_prompt
                    self.history_list[0] = {"role": "user", "content": self.role_prompt}
                    self.history_list[1] = {"role": "assistant", "content": '好的，我明白了，现在就开始，我会严格按照要求来。'}
                else:
                    # 之前没有设置role_prompt
                    self.history_list.insert(0, {"role": "user", "content": self.role_prompt})
                    self.history_list.insert(1, {"role": "assistant", "content": '好的，我明白了，现在就开始，我会严格按照要求来。'})
                    self.has_role_prompt = True
        else:
            # 删除role_prompt
            if self.has_role_prompt:
                if len(self.history_list)>0:
                    self.history_list.pop(0)
                if len(self.history_list)>0:
                    self.history_list.pop(0)
                self.has_role_prompt = False

    # 内部openai格式的history
    def __history_add_last_turn_msg(self):
        if self.history and self.question_last_turn != '':
            question = {"role": "user", "content": self.question_last_turn}
            answer = {"role": "assistant", "content": self.answer_last_turn}
            self.history_list.append(question)
            self.history_list.append(answer)
            if self.history_turn_num_now < self.history_max_turns:
                self.history_turn_num_now += 1
            else:
                if self.history_clear_method == 'pop':
                    print('======记忆超限，记录本轮对话、删除首轮对话======')
                    # for item in self.history_list:
                    #     print(item)
                    if self.role_prompt != '':
                        self.history_list.pop(2)
                        self.history_list.pop(2)
                    else:
                        self.history_list.pop(0)
                        self.history_list.pop(0)
                elif self.history_clear_method == 'clear':
                    print('======记忆超限，清空记忆======')
                    self.__history_clear()

    def clear_history(self):
        self.__history_clear()

    def __history_clear(self):
        self.history_list.clear()
        # self.has_role_prompt = False
        self.set_role_prompt(self.role_prompt)
        self.history_turn_num_now = 0

    # def __history_messages_with_question(self, in_question):
    #     msg_this_turn = {"role": "user", "content": in_question}
    #     if self.history:
    #         msgs = deepcopy(self.history_list)
    #         msgs.append(msg_this_turn)
    #         return msgs
    #     else:
    #         return [msg_this_turn]

    def __history_messages_with_question(self, in_question):
        # ===加入system提示===
        if self.has_role_prompt:
            # 如果设置有system提示
            msgs = []
        else:
            # 如果没有system提示
            msgs = [{
                "role": "system",
                "content": "You are a helpful assistant."
            }]
        # ===加入system提示===
        
        msg_this_turn = {"role": "user", "content": in_question}
        msgs += deepcopy(self.history_list)
        msgs.append(msg_this_turn)
        return msgs

    def print_history(self):
        print('\n\t================【LLM_Client】 对话历史================')
        # print(f'system提示: {self.role_prompt}')
        for item in self.history_list:
            print(f"\t {item['role']}: {item['content']}")
        print('\t==================【LLM_Client】 =====================')

    # Undo: 删除上一轮对话
    def undo(self):
        if self.has_role_prompt:
            reserved_num = 2
        else:
            reserved_num = 0

        if len(self.history_list) >= reserved_num + 2:
            self.history_list.pop()
            self.history_list.pop()
            self.history_turn_num_now -= 1

        # if self.question_last_turn=='':
        #     # 多次undo
        #     if self.has_role_prompt:
        #         reserved_num = 2
        #     else:
        #         reserved_num = 0
        #
        #     if len(self.history_list)>=reserved_num+2:
        #         self.history_list.pop()
        #         self.history_list.pop()
        # else:
        #     # 一次undo
        #     self.question_last_turn=''

    def get_retry_generator(self):
        self.undo()
        return self.ask_prepare(self.question_last_turn).get_answer_generator()

        # temp_question_last_turn = self.question_last_turn
        # self.undo()
        # self.ask_prepare(temp_question_last_turn).get_answer_and_sync_print()

    # 返回stream(generator)
    def ask_prepare(
            self,
            in_question,
            in_temperature=0.7,
            in_max_new_tokens=2048,
            in_clear_history=False,
            in_stream=True,
            in_retry=False,
            in_undo=False,
            in_stop=None,
    ):
        self.response_canceled = False
        # self.__history_add_last_turn_msg()

        if in_clear_history:
            self.__history_clear()

        if type(in_question)==str:
            # 输入仅为question字符串
            msgs = self.__history_messages_with_question(in_question)
        elif type(in_question)==list:
            # 输入为history list([{"role": "user", "content":'xxx'}, ...])
            msgs = in_question
        else:
            raise Exception('ask_prepare(): in_question must be str or list')

        # ==========================================================
        # print('发送到LLM的完整提示: ', msgs)
        # print(f'------------------------------------------------------------------------------------------')
        print(f'{"-"*80}')
        print(f'【LLM_Client】 ask_prepare(): temperature={self.temperature}')
        print(f'【LLM_Client】 ask_prepare(): messages')
        for chat in msgs:
            print(f'{chat}')
        print(f'【LLM_Client】 ask_prepare(): stream={in_stream}')
        print(f'【LLM_Client】 ask_prepare(): max_tokens={in_max_new_tokens}')

        # ==========================================================

        if self.need_print:
            print('User: \n\t', msgs[-1]['content'])
        if in_stop is None:
            stop = ['<|im_end|>', '<|im_start|>', '</s>', 'human', 'Human', 'assistant', 'Assistant']
            # stop = ['</s>', '人类', 'human', 'Human', 'assistant', 'Assistant']
        else:
            stop = in_stop
            
        print(f'【LLM_Client】 ask_prepare(): stop={stop}')


        if sys.platform.startswith('win'):
            gen = openai.ChatCompletion.create(
                model=self.model,
                temperature=in_temperature,
                # top_k=self.top_k,
                system=self.role_prompt if self.has_role_prompt else "You are a helpful assistant.",
                messages=msgs,
                stream=in_stream,
                max_new_tokens=in_max_new_tokens,   # 目前openai_api未实现（应该是靠models下的配置参数指定）
                # max_length=in_max_new_tokens,  # 目前openai_api未实现（应该是靠models下的配置参数指定）
                # stop=stop,    # win下为openai 0.28.1，不支持stop
                # Specifying stop words in streaming output format is not yet supported and is under development.
            )
        elif sys.platform.startswith('linux'):
            gen = self.openai.chat.completions.create(
                model=self.model,
                temperature=in_temperature,
                # top_k=self.top_k,
                # system=self.role_prompt if self.has_role_prompt else "You are a helpful assistant.",  # vllm目前不支持qwen的system这个参数
                messages=msgs,
                stream=in_stream,
                # max_new_tokens=in_max_new_tokens,   # 目前openai_api未实现（应该是靠models下的配置参数指定）
                max_tokens=in_max_new_tokens,  # 目前openai_api未实现（应该是靠models下的配置参数指定）
                stop=stop,
                # Specifying stop words in streaming output format is not yet supported and is under development.
            )

        self.gen = gen

        self.question_last_turn = in_question
        return self

    def ask_block(self, in_question, in_clear_history=False, in_max_new_tokens=2048, in_retry=False, in_undo=False):
        # self.__history_add_last_turn_msg()

        if in_clear_history:
            self.__history_clear()

        msgs = self.__history_messages_with_question(in_question)
        if self.need_print:
            print('User:\n\t', msgs[0]['content'])
        # openai.api_base = self.url

        if sys.platform.startswith('win'):
            res = openai.chat.completion.create(
                model=self.model,
                temperature=self.temperature,
                messages=msgs,
                stream=False,
                max_tokens=in_max_new_tokens,
                functions=[
                    {
                        'name':'run_code',
                        'parameters': {'type': 'object'}
                    }
                ]
                # Specifying stop words in streaming output format is not yet supported and is under development.
            )
        elif sys.platform.startswith('linux'):
            res = self.openai.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=msgs,
                stream=False,
                max_tokens=in_max_new_tokens,
                functions=[
                    {
                        'name':'run_code',
                        'parameters': {'type': 'object'}
                    }
                ]
                # Specifying stop words in streaming output format is not yet supported and is under development.
            )
        result = res['choices'][0]['message']['content']
        if self.need_print:
            print(f'Qwen:\n\t{result}')
        return res

    # 方式1：直接输出结果
    def get_answer_and_sync_print(self):
        result = ''
        if self.need_print:
            print('Assistant: \n\t', end='')
        for chunk in self.gen:
            if self.response_canceled:
                break

            # print(f'chunk: {chunk}')
            if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
                if self.need_print:
                    print(chunk.choices[0].delta.content, end="", flush=True)
                result += chunk.choices[0].delta.content
                # yield chunk.choices[0].delta.content
        if self.need_print:
            print()
        self.answer_last_turn = result
        self.__history_add_last_turn_msg()

        return result

    # 方式2：返回generator，在合适的时候输出结果
    def get_answer_generator(self):
        answer = ''
        for chunk in self.gen:
            if self.response_canceled:
                break

            if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
                # print(chunk.choices[0].delta.content, end="", flush=True)
                answer += chunk.choices[0].delta.content
                yield chunk.choices[0].delta.content

        self.answer_last_turn = answer
        self.__history_add_last_turn_msg()

    # 取消正在进行的stream
    def cancel_response(self):
        self.response_canceled = True

def main():
    llm = LLM_Client(
        history=True,
        history_max_turns=50,
        history_clear_method='pop',
        temperature=0.7,
        url='http://127.0.0.1:8001/v1'
    )
    while True:
        query = input('User: ')
        llm.ask_prepare(query, in_max_new_tokens=500).get_answer_and_sync_print()

if __name__ == "__main__" :
    main()


