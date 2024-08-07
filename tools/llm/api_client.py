from copy import deepcopy
# import os, requests, torch

import sys, time
from uuid import uuid4

import asyncio
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx

import config
from tools.qa.long_content_qa import short_content_qa, long_content_qa_concurrently
from utils.task import Flicker_Task
from utils.string_util import str_remove_partial_stops

from config import dred, dgreen

from openai import OpenAI
import openai
# import openai.types.completion_usage.CompletionUsage

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from redis_client import Redis_Client

# DEBUG = True
DEBUG = False

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)
    else:
        pass

@dataclass
class LLM_Client_Status:
    uuid: Optional[str] = None
    url: Optional[str] = None
    question: Optional[str] = None
    model_id: Optional[str] = None
    stops: Optional[List[str]] = field(default_factory=list)
    temperature: Optional[float] = None
    system_prompt: Optional[str] = None
    role_prompt: Optional[str] = None
    max_new_tokens: Optional[int] = None
    has_history: Optional[bool] = None
    history_list: Optional[List[Dict]] = field(default_factory=list)
    last_response: Optional[str] = None

def status_to_redis(in_status: LLM_Client_Status):
    dict = asdict(in_status)
    # redis = Redis_Client(host='192.168.124.33', port=8010, invoker='api_client')  # win-server
    # redis.set_dict(f'LLM_Client status', dict)
    # # redis.set_dict(f'client uuid', in_status.uuid)
    # # redis.set_dict(f'client url', in_status.url)
    # redis.set_dict(f'client question', in_status.question)
    # # redis.set_dict(f'client model_id', in_status.model_id)
    # redis.set_dict(f'client stops', in_status.stops)
    # redis.set_dict(f'client temperature', in_status.temperature)
    # redis.set_dict(f'client system_prompt', in_status.system_prompt)
    # redis.set_dict(f'client role_prompt', in_status.role_prompt)
    # # redis.set_dict(f'client max_new_tokens', in_status.max_new_tokens)
    # # redis.set_dict(f'client has_history', in_status.has_history)
    # redis.set_dict(f'client history_list', in_status.history_list)
    # redis.set_dict(f'client last_response', in_status.last_response)

class LLM_Client:
    LLM_SERVER = 'http://127.0.0.1:8001/v1/'
    def __init__(self,
                 history=True,
                 history_max_turns=config.Global.llm_max_chat_turns,
                 model_id=None,
                 history_clear_method='pop',
                 api_key='empty',
                 # api_key='b1ad5dac212f563be4765b646543ca1b',
                 temperature=0.7,
                 url=None,
                 max_new_tokens=512,
                 print_input=True,
                 print_output=True
                 ):
        dprint(f'【LLM_Client】 LLM_Client() inited.')

        if url is None:
            self.url = LLM_Client.Get_All_LLM_Server()
        else:
            self.url = url

        self.openai = None
        self.model_id = None
        self.api_key = api_key

        self.uuid = str(uuid4())
        self.gen = None     # 返回结果的generator
        self.usage = None   # 返回 usage={'prompt_tokens': 21, 'total_tokens': 38, 'completion_tokens': 17}
        self.stop = None    # 用于对vllm的openai api的stop进行过滤
        self.response_canceled = False  # response过程是否被中断
        self.temperature = temperature
        self.system_prompt = config.Global.llm_system_prompt
        # self.system_prompt = '' # 系统提示
        # self.top_p = top_p
        self.max_new_tokens = max_new_tokens
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
        self.print_input = print_input
        self.print_output = print_output

        self.status = LLM_Client_Status(
            uuid=self.uuid,
            url=self.url,
            model_id=self.model_id,
            temperature=self.temperature,
            max_new_tokens=self.max_new_tokens,
            has_history=self.history,
        )
        status_to_redis(self.status)

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
    @classmethod
    def Set_All_LLM_Server(cls, in_url):
        cls.LLM_SERVER = in_url

    @classmethod
    def Get_All_LLM_Server(cls):
        return cls.LLM_SERVER

    def refresh_endpoint(self, in_url, in_key, in_model_id):
        dred(f'refresh url: {in_url}')
        dred(f'refresh model id: {in_model_id}')
        dred(f'refresh api_key: {in_key}')
        if self.url != in_url or self.model_id !=in_model_id or self.api_key != in_key:
            dred(f'self.url: {self.url}')
            dred(f'in_url: {in_url}')
            dred(f'self.model_id: {self.model_id}')
            dred(f'in_model_id: {in_model_id}')

            dred(f'self.api_key: {self.api_key}')
            dred(f'in_key: {in_key}')
            dred(f'refresh_endpoint(): history cleared.')
            # self.clear_history()
            self.url = in_url
            self.model_id = in_model_id
            self.api_key = in_key


            self.openai = OpenAI(
                api_key=self.api_key,
                base_url=self.url,
            )
            if self.model_id is None or self.model_id=='':
                try:
                    self.model_id = self.openai.models.list().data[0].id
                except Exception as e:
                    dred(f'【LLM_Client异常】refresh_endpoint(): "{e}"')
                    dred(f'【LLM_Client异常】refresh_endpoint(): 可能是IP或Port设置错误，当前url为: {self.url}')
                    self.model_id = 'default'
                    # return False

            dprint(f'【LLM_Client】refresh_endpoint(): {self.url}(model_id: {self.model_id}, api_key: "{self.api_key}")')
            return True
        else:
            return False

    def set_system_prompt(self, in_system_prompt):
        self.system_prompt = in_system_prompt

        self.status.system_prompt = in_system_prompt
        # dred(f'--------system_prompt: {in_system_prompt}')
        status_to_redis(self.status)

    def set_role_prompt(self, in_role_prompt):
        if in_role_prompt.strip() != '':
            # role_prompt有内容
            self.role_prompt = in_role_prompt

            # qwen-72b和qwen-1.8b
            if sys.platform.startswith('win'):          # win下用的是qwen的openai api
                # if self.has_role_prompt and len(self.history_list)>0 :
                #     # 之前已经设置role_prompt
                #     self.history_list[0] = {"role": "system", "content": self.role_prompt}
                # else:
                #     # 之前没有设置role_prompt
                #     self.history_list.insert(0, {"role": "system", "content": self.role_prompt})
                #     self.has_role_prompt = True

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
                self.role_prompt = ''

        self.status.role_prompt = in_role_prompt
        # dred(f'--------------status: {self.status}')
        status_to_redis(self.status)

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
                    dred('======对话轮次超限，记录本轮对话、删除首轮对话======')
                    # for item in self.history_list:
                    #     print(item)
                    if self.has_role_prompt:
                        # 有role prompt，则删除第二个对话
                        self.history_list.pop(2)
                        self.history_list.pop(2)
                    else:
                        # 没有role prompt，则删除第一个对话
                        self.history_list.pop(0)
                        self.history_list.pop(0)
                elif self.history_clear_method == 'clear':
                    dred('======对话轮次超限，清空记忆======')
                    self.__history_clear()

    def clear_history(self):
        dred(f'----------------------------------------------------clear_history() invoked!----------------------------------------------------')
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

    def __history_messages_with_system_and_new_question(self, in_question):
        # ===加入system提示===
        msgs = [{
            "role": "system",
            "content": self.system_prompt,
            # "content": "You are a helpful assistant."
        }]

        msg_this_turn = {"role": "user", "content": in_question}
        msgs += deepcopy(self.history_list)
        msgs.append(msg_this_turn)
        return msgs

    def print_history_and_system(self):
        # print('\n\t================【LLM_Client】 对话历史================')
        # print(f'system提示: {self.role_prompt}')
        dgreen(f"\n\tsystem: \t{self.system_prompt}")
        for chat in self.history_list:
            content = chat['content'][:50]+'...' if len(chat['content']) > 50 else chat['content']
            dgreen(f"\t{chat['role']}: \t{content}")
        # print('\t==================【LLM_Client】 =====================')

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

    def get_prompt_tokens(self):
        if self.usage is not None:
            return self.usage['prompt_tokens']
        else:
            return 0
    def get_completion_tokens(self):
        if self.usage is not None:
            return self.usage['completion_tokens']
        else:
            return 0

    # 返回stream(generator)
    def ask_prepare(
            self,
            in_question,
            in_temperature=None,
            in_max_new_tokens=None,
            # in_top_p=None,
            in_clear_history=False,
            in_stream=True,
            in_retry=False,
            in_undo=False,
            in_stop=None,
            in_system_prompt=None,
    ):
        dprint(f'{"-" * 40}输入参数{"-" * 40}')
        dprint(f'self.url: "{self.url}"')
        dprint(f'self.model_id: "{self.model_id}"')
        dprint(f'self.api_key: "{self.api_key}"')

        dprint(f'in_temperature: {in_temperature}')
        dprint(f'in_stream: {in_stream}')
        dprint(f'in_max_new_tokens: {in_max_new_tokens}')
        dprint(f'in_stop: {in_stop}')
        dprint(f'in_question: "【{in_question}】"')
        dprint(f'{"-" * 40}采用参数{"-" * 40}')

        self.openai = OpenAI(
            api_key=self.api_key,
            base_url=self.url,
        )
        try:
            if self.model_id is None or self.model_id=='':
                self.model_id = self.openai.models.list().data[0].id
        except Exception as e:
            print(f'【LLM_Client异常】ask_prepare(): "{e}"')
            print(f'【LLM_Client异常】ask_prepare(): 可能是IP或Port设置错误，当前url为: {self.url}')
            self.model_id = 'wrong'

        if in_system_prompt is not None:
            self.set_system_prompt(in_system_prompt)
        # else:
        #     self.set_system_prompt(config.Global.llm_system)

        self.usage = None   # 清空输入和输出的token数量统计

        if not in_max_new_tokens:
            max_new_tokens = self.max_new_tokens
        else:
            max_new_tokens = in_max_new_tokens
        self.response_canceled = False
        # self.__history_add_last_turn_msg()

        if in_clear_history:
            self.__history_clear()

        if type(in_question)==str:
            # 输入仅为question字符串
            msgs = self.__history_messages_with_system_and_new_question(in_question)
        elif type(in_question)==list:
            # 输入为history list([{"role": "user", "content":'xxx'}, ...])
            msgs = in_question
        else:
            raise Exception('ask_prepare(): in_question must be str or list')

        # ==========================================================
        # print('发送到LLM的完整提示: ', msgs)
        # print(f'------------------------------------------------------------------------------------------')
        if in_temperature is None:
            run_temperature = self.temperature
        else:
            run_temperature = in_temperature
            
        # if in_top_p is None:
        #     run_top_p = self.top_p
        # else:
        #     run_top_p = in_top_p

        # msgs_string = ''
        # for msg in msgs:
        #     msgs_string += msg['role'] + ':\t'
        #     msgs_string += msg['content'][:50] + '\n'
        # # print(f'msgs: {msgs}')
        # # msgs_string = '\n'.join(msgs)
        # dgreen(f'query: "\n{msgs_string[:300]}...\n"(len: {len(msgs_string)})')
        # # print(f'query: "{msgs_string[:100]}..."(len: {len(msgs_string)}, url: "{self.url}")')

        # dprint(f'{"-"*80}')
        # dprint(f'【LLM_Client】 ask_prepare(): in_temperature={in_temperature}')
        # dprint(f'【LLM_Client】 ask_prepare(): self.temperature={self.temperature}')
        # dprint(f'【LLM_Client】 ask_prepare(): 最终选择run_temperature={run_temperature}')
        # dprint(f'【LLM_Client】 ask_prepare(): messages')
        # for chat in msgs:
        #     dprint(f'{chat}')
        # dprint(f'【LLM_Client】 ask_prepare(): stream={in_stream}')
        # dprint(f'【LLM_Client】 ask_prepare(): max_new_tokens={max_new_tokens}')

        # ==========================================================

        if self.print_input:
            print('<User>\n', msgs[-1]['content'])
        if in_stop is None:
            # stop = ['<|im_end|>', '<|im_start|>']
            # stop = ['<|im_end|>', '<|im_start|>', 'assistant', 'Assistant', '<step>']
            # stop = ['<|im_end|>', '<|im_start|>', '<s>', '</s>', 'human', 'Human', 'assistant', 'Assistant', '<step>']
            stop = None
        else:
            # stop = ['<|im_end|>', '<|im_start|>'] + in_stop
            # stop = ['<|im_end|>', '<|im_start|>', 'assistant', 'Assistant', '<step>'] + in_stop
            # stop = ['<|im_end|>', '<|im_start|>', '<s>', '</s>', 'human', 'Human', 'assistant', 'Assistant', '<step>'] + in_stop
            stop = in_stop

        self.stop = stop

        dprint(f'{"-" * 80}')
        # dprint(f'self.openai: {self.openai}')
        dprint(f'self.model_id: "{self.model_id}"')
        dprint(f'run_temperature: {run_temperature}')
        dprint(f'stream: {in_stream}')
        dprint(f'max_tokens: {max_new_tokens}')
        dprint(f'stop: {stop}')
        dprint(f'messages: {msgs}')

        self.status.question = in_question
        self.status.model_id = self.model_id
        self.status.temperature = run_temperature
        self.status.max_new_tokens = max_new_tokens
        self.status.stops = stop
        self.status.system_prompt = self.system_prompt
        status_to_redis(self.status)


        try:
            # dred('当前系统: windows')
            # gen = openai.ChatCompletion.create(
            #     model=self.model_id,
            #     temperature=run_temperature,
            #     # top_k=self.top_k,
            #     # top_p = run_top_p,
            #     system=self.role_prompt if self.has_role_prompt else "You are a helpful assistant.",
            #     messages=msgs,
            #     stream=in_stream,
            #     max_new_tokens=max_new_tokens,   # 目前openai_api未实现（应该是靠models下的配置参数指定）
            #     # max_length=max_new_tokens,  # 目前openai_api未实现（应该是靠models下的配置参数指定）
            #     # stop=stop,    # win下为openai 0.28.1，不支持stop
            #     # Specifying stop words in streaming output format is not yet supported and is under development.
            # )

            gen = self.openai.chat.completions.create(
                model=self.model_id,
                temperature=run_temperature,
                # top_k=self.top_k,
                # top_p = run_top_p,
                # system=self.role_prompt if self.has_role_prompt else "You are a helpful assistant.",  # vllm目前不支持qwen的system这个参数
                messages=msgs,
                stream=in_stream,
                # max_new_tokens=max_new_tokens,   # 目前openai_api未实现（应该是靠models下的配置参数指定）
                max_tokens=max_new_tokens,  # 目前openai_api未实现（应该是靠models下的配置参数指定）
                stop=stop,
                # stop_token_ids=[151329, 151336, 151338],    # glm9b-chat-1m
                # Specifying stop words in streaming output format is not yet supported and is under development.

                stream_options={"include_usage": True}, # 最新版本openai的要求
            )
            dprint(f'===self.openai.chat.completions.create() invoked.===')
            dprint(f'{"-" * 80}')
        except Exception as e:
            print(f'【LLM_Client异常】ask_prepare(): {e}')
            print('返回gen = None')
            self.question_last_turn = in_question
            return self

        self.gen = gen

        self.question_last_turn = in_question
        return self

    # def ask_block(self, in_question, in_clear_history=False, in_max_new_tokens=None, in_retry=False, in_undo=False):
    #     if not in_max_new_tokens:
    #         max_new_tokens = self.max_new_tokens
    #     else:
    #         max_new_tokens = in_max_new_tokens
    #
    #     # self.__history_add_last_turn_msg()
    #
    #     if in_clear_history:
    #         self.__history_clear()
    #
    #     msgs = self.__history_messages_with_system_and_new_question(in_question)
    #     if self.print_input:
    #         print('【User】\n\t', msgs[0]['content'])
    #     # openai.api_base = self.url
    #
    #     if sys.platform.startswith('win'):
    #         res = openai.chat.completion.create(
    #             model=self.model,
    #             temperature=self.temperature,
    #             messages=msgs,
    #             stream=False,
    #             max_tokens=max_new_tokens,
    #             functions=[
    #                 {
    #                     'name':'run_code',
    #                     'parameters': {'type': 'object'}
    #                 }
    #             ]
    #             # Specifying stop words in streaming output format is not yet supported and is under development.
    #         )
    #     elif sys.platform.startswith('linux'):
    #         res = self.openai.chat.completions.create(
    #             model=self.model,
    #             temperature=self.temperature,
    #             messages=msgs,
    #             stream=False,
    #             max_tokens=max_new_tokens,
    #             functions=[
    #                 {
    #                     'name':'run_code',
    #                     'parameters': {'type': 'object'}
    #                 }
    #             ]
    #             # Specifying stop words in streaming output format is not yet supported and is under development.
    #         )
    #     result = res['choices'][0]['message']['content']
    #     if self.print_output:
    #         print(f'<Assistant>\n\t{result}')
    #     return res

    # 方式1：直接输出结果
    # def get_answer_and_sync_print(self):
    #     result = ''
    #     if self.print_output:
    #         print('<Assistant>\n', end='')
    #     for chunk in self.gen:
    #         if self.response_canceled:
    #             break
    #
    #         # print(f'chunk: {chunk}')
    #         if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
    #             if self.print_output:
    #                 print(chunk.choices[0].delta.content, end="", flush=True)
    #             result += chunk.choices[0].delta.content
    #             # yield chunk.choices[0].delta.content
    #     if self.print_output:
    #         print()
    #     self.answer_last_turn = result
    #     self.__history_add_last_turn_msg()
    #
    #     return result
    def get_answer_and_sync_print(self):
        result = ''

        dred('<assistant>')
        for chunk in self.get_answer_generator():
            result += chunk
            dred(chunk, end='', flush=True)

        # dgreen(' \n\n', flush=True)
        return result

    # 方式2：返回generator，在合适的时候输出结果
    def get_answer_generator(self):
        answer = ''
        answer_no_partial_stop = ''
        perhaps_stop_string = ''    # 非常重要，用于存放疑似stop的缓冲

        try:
            # dprint(f'self.gen: {self.gen}')
            for chunk in self.gen:
                # dprint(f'chunk: {chunk}')
                if self.response_canceled:
                    break

                # print(f'chunk.choices[0].delta: {chunk.choices[0].delta}')
                # print(f'chunk: {chunk}')
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    self.usage = {}
                    self.usage['prompt_tokens'] = chunk.usage.prompt_tokens
                    self.usage['total_tokens'] = chunk.usage.total_tokens
                    self.usage['completion_tokens'] = chunk.usage.completion_tokens

                if chunk.choices and hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
                    # if hasattr(chunk, 'usage') and chunk.usage is not None:
                    #     print(f'chunk.usage: {chunk.usage}')
                    #     # 输入和输出的token数量统计
                    #     # dred(f'usage = {chunk.usage}')
                    #     # dred(f'type(usage) = {type(chunk.usage)}')
                    #     if type(chunk.usage) is openai.types.completion_usage.CompletionUsage:
                    #         # deepseek API采用openai.types.completion_usage.CompletionUsage: CompletionUsage(completion_tokens=50, prompt_tokens=18, total_tokens=68)
                    #         self.usage = {}
                    #         self.usage['prompt_tokens'] = chunk.usage.prompt_tokens
                    #         self.usage['total_tokens'] = chunk.usage.total_tokens
                    #         self.usage['completion_tokens'] = chunk.usage.completion_tokens
                    #     else:
                    #         # vllm API采用: {'prompt_tokens': 21, 'total_tokens': 38, 'completion_tokens': 17}
                    #         self.usage = chunk.usage

                    my_chunk = chunk.choices[0].delta.content
                    answer += my_chunk

                    if self.stop:
                        # 进行stop的增强修正(vllm的stop机制有bug，有时agent中的特殊stop如"观察"无法正确停止)
                        answer_no_partial_stop = str_remove_partial_stops(answer, self.stop)

                        # print(f'answer1: {answer}')
                        # print(f'answer2: {answer_no_partial_stop}')
                        if answer_no_partial_stop == answer:
                            my_chunk = perhaps_stop_string + my_chunk   # 1、将证实不是stop的字符补在前面
                            perhaps_stop_string = ''                    # 2、清空疑似stop的缓冲
                            # 没partial_stop
                            # print(my_chunk, end='', flush=True)
                            yield my_chunk
                        else:
                            perhaps_stop_string += my_chunk #存放疑似stop的缓冲，后面如果证实不是stop，需要补回去
                            # 有partial_stop
                            # print(f'*{my_chunk}*', end='', flush=True)
                            yield ''
                    else:
                        # 没有stop时
                        yield my_chunk

        except Exception as e:
            dred(f'LLM_Client("{self.url}")连接异常: {e}')
            yield ''

        if self.stop:
            self.answer_last_turn = answer_no_partial_stop
        else:
            self.answer_last_turn = answer

        # self.answer_last_turn = answer
        self.__history_add_last_turn_msg()
        # self.print_history_and_system()

        self.status.last_response = answer
        self.status.history_list = self.history_list
        # dred(f'--------------self.last_response: {answer}')
        # dred(f'--------------self.history_list: {self.history_list}')
        # dred(f'--------------status: {self.status}')
        status_to_redis(self.status)

    # def get_answer_generator(self):
    #     answer = ''
    #     for chunk in self.gen:
    #         if self.response_canceled:
    #             break
    #
    #         if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
    #             my_chunk = chunk.choices[0].delta.content
    #             answer += my_chunk
    #
    #             yield my_chunk
    #
    #     self.answer_last_turn = answer
    #     self.__history_add_last_turn_msg()

    # 取消正在进行的stream
    def cancel_response(self):
        self.response_canceled = True

# async的非联网llm调用
class Async_LLM:
    def __init__(self):
        
        self.llm = None
        self.stream_buf_callback = None
        self.task = None
        self.prompt = ''
        self.role_prompt = ''
        self.extra_suffix = ''
        self.final_response = ''
        self.run_in_streamlit = False
        
        self.complete = False

        self.flicker = None

        self.getting_chunk = False
        self.chunk = ''

        self.temperature = None

    def init(self, in_stream_buf_callback, in_prompt, in_role_prompt='', in_extra_suffix='', in_streamlit=False, in_temperature=0.7):
        self.complete = False
        
        self.llm = LLM_Client(history=True, print_input=False, temperature=in_temperature)
        self.llm.set_role_prompt(in_role_prompt)
        self.stream_buf_callback = in_stream_buf_callback
        self.prompt = in_prompt
        self.role_prompt = in_role_prompt
        self.extra_suffix = in_extra_suffix # 输出的额外内容
        self.run_in_streamlit = in_streamlit

        self.flicker = Flicker_Task()

        self.temperature = in_temperature
        
    def get_final_response(self):
        return self.final_response

    def wait(self):
        if self.task:
            self.task.join()

    def run(self):
        # print(f'【Async_LLM】run(temperature={self.temperature}) invoked.')
        gen = self.llm.ask_prepare(self.prompt).get_answer_generator()
        full_response = ''

        # 将for chunk in gen的同步next(gen)改造为异步，从而在stream暂时没有数据时，从而让光标闪烁等事件能够被响应。
        self.chunk = ''
        self.getting_chunk = False
        while not self.complete:
            def get_chunk():
                if not self.getting_chunk:
                    self.getting_chunk = True
                    try:
                        self.chunk=next(gen)
                    except StopIteration as e:
                        self.complete = True
                    self.getting_chunk = False

            if not self.getting_chunk:
                full_response += self.chunk
                self.final_response = full_response
                t = threading.Thread(target=get_chunk)
                t.start()
                #chunk = next(gen)    
                    
            self.stream_buf_callback(full_response + self.flicker.get_flicker())
            time.sleep(0.05)

        # 注意：vllm并行query刚开始时，这行代码这里会卡死2-3秒钟。因此需要改造为异步，从而让光标闪烁等事件能够被响应。
        # for chunk in gen:
        #     full_response += chunk
        #     self.stream_buf_callback(full_response + self.flicker.get_flicker())
        
        # print(f'【Async_LLM】extra_suffix= {self.extra_suffix}')
        full_response += self.extra_suffix
        self.stream_buf_callback(full_response)

        self.final_response = full_response

        dprint(f'【Async_LLM】run() completed. temperature={self.temperature}, final_response="{self.final_response}"')

    def start(self):
        # 由于streamlit对thread支持不好，这里必须在threading.Thread(target=self.run)之后紧跟调用add_script_run_ctx(t)才能正常调用run()里面的st.markdown()这类功能，不然会报错：missing xxxxContext
        self.task = threading.Thread(target=self.run)
        if self.run_in_streamlit:
            add_script_run_ctx(self.task)
        
        self.task.start()
        self.flicker.init(flicker1='█ ', flicker2='  ').start()

    async def wrong_run(self):
        dprint(f'Async_LLM._stream_output_process() invoked.')
        gen = self.llm.ask_prepare(self.prompt).get_answer_generator()
        full_response = ''
        for chunk in gen:
            full_response += chunk
            self.full_response = full_response
            self.stream_buf_callback(full_response)

    def wrong_start(self):
        # 创建async任务
        new_loop = asyncio.new_event_loop()  # 子线程下新建时间循环
        asyncio.set_event_loop(new_loop)
        self.task = asyncio.ensure_future(self.wrong_run())
        # loop = asyncio.new_event_loop()
        # self.task = loop.create_task(self._stream_output_process())    # create_task()没有方便的非阻塞运行方式 
        # self.task = asyncio.create_task(self._stream_output_process())    # 该行在streamlit下报错：no running event loop
        new_loop.run_until_complete(self.task)    # 改行是阻塞等待task完成
        dprint(f'Async_LLM.start() invoked.')
    
# 通过多个llm的client，对model进行并发访问，同步返回多个stream
class Concurrent_LLMs:
    def __init__(self, in_url='http://127.0.0.1:8001/v1/'):
        self.prompts = []
        self.role_prompts = []
        self.contents = []
        self.content_short_enough = True
        
        self.stream_buf_callback = None
        self.llms = []
        self.llms_post_processed = []

        self.cursor = ''
        self.flicker = None

        self.url = in_url

        self.all_finished = False

    def init(
        self,
        in_prompts,             # 输入的多个prompt
        in_contents,            # 输入的多个长文本(需要分别嵌入prompt进行解读)
        in_stream_buf_callbacks=None,# 用于执行stream输出的回调函数list(该回调函数list可以是[streamlit.empty[].markdown, ...])
        in_role_prompts=None,   # 输入的多个role prompt
        in_extra_suffixes=None, # 输出的额外内容(维度同上)
        in_cursor='█ ',         # 输出未完成时显示用的光标
        in_max_new_tokens=2048,
        in_content_short_enough=True,  # 如果short_enough, 则每个qa只需要调用short_content_qa而不用调用long_content_qa(分段)
    ):
        self.prompts = in_prompts
        self.contents = in_contents
        self.content_short_enough = in_content_short_enough
        self.stream_buf_callbacks = in_stream_buf_callbacks
        self.role_prompts = in_role_prompts
        self.cursor = in_cursor
        self.extra_suffixes = in_extra_suffixes

        x = 0
        print('---------------Concurrent_LLMs.init()---------------')
        for content in self.contents:
            x += 1
            one_line_content = ''.join(content.split('\n'))
            print(f'content[{x}]内容(长度{len(content)}): "{one_line_content[:50]}..."')
        print('--------------------------------------------------------------------')

        # 初始化所有llm
        for prompt in self.prompts:
            self.llms.append(LLM_Client(history=False, max_new_tokens=in_max_new_tokens, print_input=False, temperature=0, url=self.url))
            self.llms_post_processed.append(False)
        self.llms_num = len(self.llms)

        self.flicker = Flicker_Task()
        self.flicker.init(flicker1='█ ', flicker2='  ').start()

    # 用于yield返回状态：
    # status = {
    #     'status_type'         : 'complete/running',         # 对应streamlit中的status.update中的state参数(complete, running)
    #     'canceled'            : False,                      # 整个任务是否canceled
    #     'status_describe'     : '状态描述',                  # 对应streamlit中的status.update
    #     'status_detail'       : '状态细节',                  # 对应streamlit中的status.write或status.markdown
    #     'llms_complete'       : [False ， ...]              # 所有llm的完成状态(False, True)
    #     'llms_full_responses' : [''， ...]                  # 所有llm的返回文本
    # }

    def wait_all(self, in_status_gen):
        for status in in_status_gen:
            st = status['detail']
            print(f'[Concurrent_LLMs]: status is "{st}"')

        return status

    def start_and_get_status(self):
        llm_num = self.llms_num
        extra_suffixes = self.extra_suffixes if self.extra_suffixes else [''] * llm_num

        # 整体状态和所有llm的状态
        status = {
            'type'                : 'running',
            'canceled'            : False,
            'describe'            : '启动解读任务...', 
            'detail'              : f'所有llm已完成初始化，llm数量为{llm_num}.',
            'llms_complete'       : [False]*llm_num,
            'llms_full_responses' : ['']*llm_num,
        }
        yield status

        # 启动所有llm，并注册llms_gens
        llms_gens = []
        for i in range(llm_num):
            # 返回联网分析结果
            # print(f'self.content_short_enough: {self.content_short_enough}')
            if self.content_short_enough:
                # llms_gens.append(long_content_qa_concurrently(self.llms[i], self.contents[i], self.prompts[i]))
                llms_gens.append(short_content_qa(self.llms[i], self.contents[i], self.prompts[i]))
            else:
                llms_gens.append(long_content_qa_concurrently(self.llms[i], self.contents[i], self.prompts[i]))
                # llms_gens.append(long_content_qa(self.llms[i], self.contents[i], self.prompts[i]))

        status['detail'] = '所有llm的文本解读已启动...'
        yield status

        while True:
            if all(status['llms_complete']):
                # 所有llm均已完成回复stream，则退出
                status['type'] = 'complete'
                status['describe'] = '解读任务已完成.'
                status['detail'] = '所有llm的文本解读任务已完成.'

                self.all_finished = True
                yield status
                break

            i = 0
            for gen in llms_gens:
                # 遍历每一个llm的回复stream的chunk
                try:
                    if gen == []:
                        # 出现超限等问题时返回的[]
                        status['llms_full_responses'][i] = '服务器错误: llm输入长度超限.'
                        status['llms_complete'][i] = True
                    else:
                        # 正常返回stream
                        chunk = next(gen)
                        status['llms_full_responses'][i] += chunk

                    # 测试输出
                    if i==0:
                        dprint(chunk, end='')
                        
                except StopIteration as e:
                    # 如果next引发StopIteration异常，则设置finished为True
                    status['llms_complete'][i] = True
                except Exception as e:
                    print(f'llm[{i}] next(gen) error: "{e}"')
                    status['llms_full_responses'][i] = '服务器错误: llm输入长度超限.'
                    status['llms_complete'][i] = True

                # 向外部stream接口输出当前llm的stream chunk
                if status['llms_complete'][i] :
                    # 该llm已经完成

                    # 每一个llm的后处理
                    if not self.llms_post_processed[i]:                   
                        # extra_suffixes = self.extra_suffixes if self.extra_suffixes else ''
                        status['llms_full_responses'][i] += extra_suffixes[i]
                        self.llms_post_processed[i] = True

                    if self.stream_buf_callbacks:
                        self.stream_buf_callbacks[i](status['llms_full_responses'][i])
                else:
                    # 该llm尚未完成
                    if len(status['llms_full_responses'][i])>5:
                        # print('self.stream_buf_callbacks:', self.stream_buf_callbacks)
                        if self.stream_buf_callbacks:
                            self.stream_buf_callbacks[i](status['llms_full_responses'][i] + self.flicker.get_flicker() + '\n\n')
                    else:
                        # vllm有个初始化过程，会先返回1、2个字符，然后卡几秒钟，然后才会全速并发输出stream
                        pass
                
                i += 1

def main():
    llm = LLM_Client(
        history=True,
        history_max_turns=50,
        history_clear_method='pop',
        temperature=0.7,
        url='http://127.0.0.1:8001/v1/'
    )
    while True:
        query = input('User: ')
        llm.ask_prepare(query, in_max_new_tokens=500).get_answer_and_sync_print()

question="""
以下是一个文档的目录结构：
# World Energy Outlook 2023
## Foreword
## Acknowledgements
## Table of Contents
## Executive Summary
## Chapter 1. Overview and key findings
### Introduction
### 1.1 A peak by 2030 for each of the fossil fuels
#### 1.1.1 Coal: Scaling up clean power hastens the decline
#### 1.1.2 Oil: End of the “ICE age” turns prospects around
#### 1.1.3 Natural gas: Energy crisis marks the end of the “Golden Age”
### 1.2 A slowdown in economic growth in China would have huge implications for energy markets
#### 1.2.1 China’s growth has defined the energy world in recent decades
#### 1.2.2 Integrating a slowdown in China’s economy into the STEPS
#### 1.2.3 Sensitivities in the Outlook
### 1.3 A boom of solar manufacturing could be a boon for the world
#### 1.3.1 Solar module manufacturing and trade
#### 1.3.2 Solar PV deployment could scale up faster to accelerate transitions
### 1.4 The pathway to a 1.5 °C limit on global warming is very tough, but it remains open
#### 1.4.1 Four reasons for hope
#### 1.4.2 Four areas requiring urgent attention
### 1.5 Capital flows are gaining pace, but not reaching the areas of greatest need
#### 1.5.1 Fossil fuels
#### 1.5.2 Clean energy
### 1.6 Transitions have to be affordable
#### 1.6.1 Affordability for households
#### 1.6.2 Affordability for industry
#### 1.6.3 Affordability for governments
### 1.7 Risks on the road to a more electrified future
#### 1.7.1 Managing risks for rapid electrification
#### 1.7.2 Critical minerals underpin electrification
### 1.8 A new, lower carbon pathway for emerging market and developing economies is taking shape
### 1.9 Geopolitical tensions undermine energy security and prospects for rapid, affordable transitions
#### 1.9.1 Clean energy in a low-trust world
#### 1.9.2 Fossil fuels in a low-trust world
#### 1.9.3 Risks of new dividing lines
### 1.10 As the facts change, so do our projections
#### 1.10.1 Solar PV and wind generation
#### 1.10.2 Natural gas
## Chapter 2. Setting the scene
### 2.1 New context for the World Energy Outlook
#### 2.1.1 New clean energy economy
#### 2.1.2 Uneasy balance for oil, natural gas and coal markets
#### 2.1.3 Key challenges for secure and just clean energy transitions
### 2.2 WEO Scenarios
#### 2.2.1 Policies
#### 2.2.2 Economic and demographic assumptions
#### 2.2.3 Energy, critical mineral and carbon prices
#### 2.2.4 Technology costs
## Chapter 3. Pathways for the energy mix
### 3.1 Introduction
### 3.2 Overview
### 3.3 Total final energy consumption
#### 3.3.1 Industry
#### 3.3.2 Transport
#### 3.3.3 Buildings
### 3.4 Electricity
### 3.5 Fuels
#### 3.5.1 Oil
#### 3.5.2 Natural gas
#### 3.5.3 Coal
#### 3.5.4 Modern bioenergy
### 3.6 Key clean energy technology trends
## Chapter 4. Secure and people-centred energy transitions
### 4.1 Introduction
### 4.2 Environment and climate
#### 4.2.1 Emissions trajectory and temperature outcomes
#### 4.2.2 Methane abatement
#### 4.2.3 Air quality
### 4.3 Secure energy transitions
#### 4.3.1 Fuel security and trade
#### 4.3.2 Electricity security
#### 4.3.3 Clean energy supply chains and critical minerals
### 4.4 People-centred transitions
#### 4.4.1 Energy access
#### 4.4.2 Energy affordability
#### 4.4.3 Energy employment
#### 4.4.4 Behavioural change
### 4.5 Investment and finance needs
## Chapter 5. Regional insights
### 5.1 Introduction
### 5.2 United States
#### 5.2.1 Key energy and emissions trends
#### 5.2.2 How much have the US Inflation Reduction Act and other recent policies changed the picture for clean energy transitions?
### 5.3 Latin America and the Caribbean
#### 5.3.1 Key energy and emissions trends
#### 5.3.2 What role for Latin America and the Caribbean in maintaining traditional oil and gas security through energy transitions?
#### 5.3.3 Do critical minerals open new avenues for Latin America and the Caribbean’s natural resources?
### 5.4 European Union
#### 5.4.1 Key energy and emissions trends
#### 5.4.2 Can the European Union deliver on its clean energy and critical materials targets?
#### 5.4.3 What next for the natural gas balance in the European Union?
### 5.5 Africa
#### 5.5.1 Key energy and emissions trends
#### 5.5.2 Recharging progress towards universal energy access
#### 5.5.3 What can be done to enhance energy investment in Africa?
### 5.6 Middle East
#### 5.6.1 Key energy and emissions trends
#### 5.6.2 Shifting fortunes for energy exports
#### 5.6.3 How is the desalination sector changing in times of increasing water needs and the energy transition?
### 5.7 Eurasia
#### 5.7.1 Key energy and emissions trends
#### 5.7.2 What’s next for oil and gas exports from Eurasia?
### 5.8 China
#### 5.8.1 Key energy and emissions trends
#### 5.8.2 How soon will coal use peak in China?
### 5.9 India
#### 5.9.1 Key energy and emissions trends
#### 5.9.2 Impact of air conditioners on electricity demand in India
#### 5.9.3 Will domestic solar PV module manufacturing keep pace with solar capacity growth in India?
### 5.10 Japan and Korea
#### 5.10.1 Key energy and emissions trends
#### 5.10.2 Challenges and opportunities of nuclear and offshore wind
#### 5.10.3 What role can hydrogen play in the energy mix and how can the governments deploy it?
### 5.11 Southeast Asia
#### 5.11.1 Key energy and emissions trends
#### 5.11.2 How can international finance accelerate clean energy transitions in Southeast Asia?
#### 5.11.3 How can regional integration help integrate more renewables?
## Annexes
### Annex A: Tables for scenario projections
### Annex B: Design of the scenarios
#### B.1 Population
#### B.2 CO2 prices
#### B.3 Fossil fuel resources
#### B.4 Electricity generation technology costs
#### B.5 Other key technology costs
#### B.6 Policies
### Annex C: Definitions
#### Units
#### General conversion factors for energy
#### Currency conversions
#### Definitions
#### Regional and country groupings
#### Abbreviations and acronyms
### Annex D: References
#### Chapter 1: Overview and key findings
#### Chapter 2: Setting the scene
#### Chapter 3: Pathways for the energy mix
#### Chapter 4: Secure and people-centred energy transitions
#### Chapter 5: Regional insights
#### Annex B: Design of the scenarios
### Annex E: Inputs to the Global Energy and Climate Model
#### General note
#### IEA databases and publications

用户现在问了一个关于该报告的问题: "报告有没有涉及投资、日韩问题、生物质的分析"，请问该问题的答案可能在报告哪个具体的章节中，请根据所提供目录结构信息，返回对应的章节标题，不要解释，直接返回如下格式：
[
    {
        'chapter_index':'x.x.x1',
        'chapter_title':'xxx1',
    },
    {
        'chapter_index':'x.x.x2',
        'chapter_title':'xxx2',
    },
]
"""

def miqu_generate_stream(in_query):
    import requests
    import json

    # 定义请求的URL和数据
    url = "http://127.0.0.1:8001/generate_stream"
    data = {
        "inputs": in_query,
        "parameters": {"max_new_tokens": 512}
    }
    headers = {'Content-Type': 'application/json'}

    # 发送POST请求，并以流式方式处理响应
    response = requests.post(url, data=json.dumps(data), headers=headers, stream=True)

    # 检查请求是否成功
    if response.status_code == 200:
        for line in response.iter_lines():
            # 打印每一行输出
            if line:
                line_string = line.decode('utf-8')
                # print(f'line_string: {line_string}')
                if line_string is not None:
                    obj = json.loads(line_string[5:])
                    print(obj['token']['text'], end='', flush=True)
                    # print(line.decode('utf-8'))
    else:
        print(f"请求失败，状态码：{response.status_code}")
    print()


def main1():
    print('main_call()')
    llm = LLM_Client(
        history=True,
        history_max_turns=50,
        history_clear_method='pop',
        model_id='miqu-1-70b-sf-GPTQ',
        temperature=0.7,
        api_key='b1ad5dac212f563be4765b646543ca1b',
        # api_key='sk-6zcUSkVMPIR2WIhjC73a27B4D7584e8cBf1f1991Cf512626',
        url='http://116.62.63.204:8001/v1/'
    )
    # print('models: ', openai.models.list().data)
    llm.ask_prepare('你是谁？', in_max_new_tokens=500).get_answer_and_sync_print()
    # llm.ask_prepare(question, in_max_new_tokens=500).get_answer_and_sync_print()

def main2():
    llm = LLM_Client(
        history=True,
        history_max_turns=50,
        history_clear_method='pop',
        temperature=0.7,
        url='http://192.168.124.33:8001/v1/'
        # url='http://localhost:8001/v1/'
    )
    # print('models: ', openai.models.list().data)
    # llm.set_system_prompt('不管我说什么，都直接把我说的话翻译为中文回复给我.')
    # llm.set_role_prompt('不管我说什么，都直接把我说的话翻译为中文回复给我.')
    llm.ask_prepare('你是谁', in_temperature=0.5, in_max_new_tokens=200).get_answer_and_sync_print()
    # llm.ask_prepare('write a word', in_temperature=0.6, in_max_new_tokens=300).get_answer_and_sync_print()
    # llm.ask_prepare('write 3 words', in_temperature=0.9, in_stop=['<s>', '|<end>|'], in_max_new_tokens=400).get_answer_and_sync_print()

if __name__ == "__main__" :
    # main1()
    main2()
