from openai import OpenAI

# 安装wcwidth
# pip install wcwidth

from copy import deepcopy
import base64, wave
from pprint import pprint
# import os, requests, torch
import requests, re

import sys, time
from uuid import uuid4

import asyncio
import threading

import config
from utils.string_util import str_remove_partial_substring_or_right, str_remove_content_in_partial_pairs, \
    _str_get_content_in_partial_pairs

from config import dred, dgreen, dblue, dcyan, dyellow

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
# from redis_client import Redis_Client

from server_manager.legacy_web_server_base import legacy_Web_Server_Base
from server_manager.web_server_task_manager import Web_Client_Data_Type, Web_Client_Data, Web_Client_Table_Data, \
    Web_Client_Text_Data, Web_Client_Image_Data
from utils.image import get_image_string_from_url
import json

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


class LLM_Client():
    LLM_SERVER = config.LLM_Default.url

    # LLM_SERVER = 'http://127.0.0.1:8001/v1/'
    def __init__(self,
                 history=None,
                 history_max_turns=config.Global.llm_max_chat_turns,
                 llm_config=None,
                 model_id=None,
                 history_clear_method='pop',
                 api_key=None,
                 # api_key='b1ad5dac212f563be4765b646543ca1b',
                 temperature=config.LLM_Default.temperature,
                 top_p=config.LLM_Default.top_p,
                 # top_p=None,
                 url=None,
                 max_new_tokens=None,
                 print_input=True,
                 print_output=True,
                 ):
        dprint(f'【LLM_Client】 LLM_Client() inited.')

        history = int(config.LLM_Default.history if history is None else history)
        api_key = config.LLM_Default.api_key if api_key is None else api_key
        temperature = config.LLM_Default.temperature if temperature is None else temperature
        url = config.LLM_Default.url if url is None else url
        max_new_tokens = config.LLM_Default.max_new_tokens if max_new_tokens is None else max_new_tokens

        self.openai = None

        # llm配置
        self.url = url
        self.model_id = model_id
        self.api_key = api_key

        self.temperature = temperature
        self.top_p = top_p
        self.max_new_tokens = max_new_tokens
        self.reasoning_effort = None
        self.vpn_on = False

        self.history_input_tokens_num = 0
        self.input_tokens_num_this_turn = 0
        self.history_output_tokens_num = 0
        self.output_tokens_num_this_turn = 0

        if llm_config:
            self.url = llm_config.base_url
            self.model_id = llm_config.llm_model_id
            self.api_key = llm_config.api_key
            self.temperature = llm_config.temperature
            self.top_p = llm_config.top_p
            self.max_new_tokens = llm_config.max_new_tokens
            self.reasoning_effort = llm_config.reasoning_effort
            self.vpn_on = llm_config.vpn_on

        dblue(f'【LLM_Client】base_url={self.url!r}')
        dblue(f'【LLM_Client】history={history!r}')
        dblue(f'【LLM_Client】model_id={self.model_id!r}')
        dblue(f'【LLM_Client】api_key={self.api_key!r}')
        dblue(f'【LLM_Client】temperature={self.temperature!r}')
        dblue(f'【LLM_Client】top_p={self.top_p!r}')
        dblue(f'【LLM_Client】max_new_tokens={self.max_new_tokens!r}')

        self.uuid = str(uuid4())
        self.gen = None  # 返回结果的generator
        self.usage = None  # 返回 usage={'prompt_tokens': 21, 'total_tokens': 38, 'completion_tokens': 17}
        self.stop = None  # 用于对vllm的openai api的stop进行过滤
        self.response_canceled = False  # response过程是否被中断

        self.system_prompt = config.Global.llm_system_prompt

        # self.system_prompt = '' # 系统提示
        # self.top_p = top_p
        # self.top_k = top_k  # 需要回答稳定时，可以不通过调整temperature，直接把top_k设置为1; 官方表示qwen默认的top_k为0即不考虑top_k的影响

        self.result_chunk_as_think_chunk = ''  # 非reason模型推理时，获取think输出时，会误将result_chunk当成think_chunk，这里要保存这个chunk，后续交给result

        # 记忆相关
        self.history_list = []
        self.history = history
        self.history_max_turns = history_max_turns
        self.history_turn_num_now = 0

        self.history_clear_method = history_clear_method  # 'clear' or 'pop'

        self.question_last_turn = ''
        self.answer_last_turn = ''

        self.role_prompt = ''
        self.has_role_prompt = False

        self.external_last_history = []  # 用于存放外部格式独特的history
        self.print_input = print_input
        self.print_output = print_output

        self.remove_content_in_think_pairs = False  # 是否remove ('<think>', '</think>') 之间的内容

        self.status = LLM_Client_Status(
            uuid=self.uuid,
            url=self.url,
            model_id=self.model_id,
            temperature=self.temperature,
            max_new_tokens=self.max_new_tokens,
            has_history=self.history,
        )
        status_to_redis(self.status)

        dyellow(f'【LLM_Client】vpn_on={self.vpn_on!r}')
        dyellow(f'【LLM_Client】system_prompt={self.system_prompt!r}')

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
        if self.url != in_url or self.model_id != in_model_id or self.api_key != in_key:
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

            if self.vpn_on:
                import httpx
                http_client = httpx.Client(
                    proxy=config.g_vpn_proxy)
                self.openai = OpenAI(
                    api_key=self.api_key,
                    base_url=self.url,
                    http_client=http_client,
                    # http_client=openai.DefaultHttpxClient(verify=False),    # 用于自建的vllm openai api的ssl访问(https访问)，# 阿里云购买了正式证书（可以是免费的）后，即可开启verify，也就是去掉本行
                )
            else:
                self.openai = OpenAI(
                    api_key=self.api_key,
                    base_url=self.url,
                    # http_client=openai.DefaultHttpxClient(verify=False),    # 用于自建的vllm openai api的ssl访问(https访问)，# 阿里云购买了正式证书（可以是免费的）后，即可开启verify，也就是去掉本行
                )
            if self.model_id is None or self.model_id == '':
                try:
                    self.model_id = self.openai.models.list().data[0].id
                    dblue(f'【LLM_Client】change model_id to "{self.model_id}"\n')
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
            if sys.platform.startswith('win'):  # win下用的是qwen的openai api
                # if self.has_role_prompt and len(self.history_list)>0 :
                #     # 之前已经设置role_prompt
                #     self.history_list[0] = {"role": "system", "content": self.role_prompt}
                # else:
                #     # 之前没有设置role_prompt
                #     self.history_list.insert(0, {"role": "system", "content": self.role_prompt})
                #     self.has_role_prompt = True

                # 早期qwen版本或其他llm
                if self.has_role_prompt and len(self.history_list) > 0:
                    # 之前已经设置role_prompt
                    self.history_list[0] = {"role": "user", "content": self.role_prompt}
                    self.history_list[1] = {"role": "assistant",
                                            "content": '好的，我明白了，现在就开始，我会严格按照要求来。'}
                else:
                    # 之前没有设置role_prompt
                    self.history_list.insert(0, {"role": "user", "content": self.role_prompt})
                    self.history_list.insert(1, {"role": "assistant",
                                                 "content": '好的，我明白了，现在就开始，我会严格按照要求来。'})
                    self.has_role_prompt = True
            elif sys.platform.startswith('linux'):  # linux下用的是vllm的openai api
                # 早期qwen版本或其他llm
                if self.has_role_prompt and len(self.history_list) > 0:
                    # 之前已经设置role_prompt
                    self.history_list[0] = {"role": "user", "content": self.role_prompt}
                    self.history_list[1] = {"role": "assistant",
                                            "content": '好的，我明白了，现在就开始，我会严格按照要求来。'}
                else:
                    # 之前没有设置role_prompt
                    self.history_list.insert(0, {"role": "user", "content": self.role_prompt})
                    self.history_list.insert(1, {"role": "assistant",
                                                 "content": '好的，我明白了，现在就开始，我会严格按照要求来。'})
                    self.has_role_prompt = True
        else:
            # 删除role_prompt
            if self.has_role_prompt:
                if len(self.history_list) > 0:
                    self.history_list.pop(0)
                if len(self.history_list) > 0:
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
            # pprint(self.history_list)
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

    def delete_history(self):
        dred(
            f'----------------------------------------------------clear_history() invoked!----------------------------------------------------')
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

    def __history_messages_with_system_and_new_question(
            self,
            question,
            image_url=None,  # image url或者base64 encoded string，不能是本地文件路径
    ):
        # ===加入system提示===
        msgs = [{
            "role": "system",
            "content": self.system_prompt,
            # "content": "You are a helpful assistant."
        }]

        if image_url is None:
            # 没有图片
            msg_this_turn = {
                "role": "user",
                "content": question
            }
        else:
            # 有图片
            msg_this_turn = {
                "role": "user",
                "content": [
                    {'type': 'text', 'text': question},
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': image_url
                        }
                    },
                ]
            }

        msgs += deepcopy(self.history_list)
        msgs.append(msg_this_turn)
        return msgs

    def print_history_and_system(self):
        # print('\n\t================【LLM_Client】 对话历史================')
        # print(f'system提示: {self.role_prompt}')
        dgreen(f"\n\tsystem: \t{self.system_prompt}")
        for chat in self.history_list:
            content = chat['content'][:50] + '...' if len(chat['content']) > 50 else chat['content']
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

    def audio_file_to_text(self, save_file_name):
        # if len(audio_string) > 0:
        #     wav_data = base64.b64decode(audio_string)
        from tools.audio_stt.audio_stt import AudioSTT
        text = AudioSTT().stt(save_file_name)
        return text

    def audio_to_wav_file(self, save_file_name, audio_string):
        if len(audio_string) > 0:
            wav_data = base64.b64decode(audio_string)
            file_name = save_file_name
            channels = 1
            sample_width = 2
            frame_rate = 44100
            with wave.open(file_name, 'wb') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(frame_rate)
                wav_file.writeframes(wav_data)

    def get_input_tokens_num_this_turn(self):
        return self.input_tokens_num_this_turn

    def get_output_tokens_num_this_turn(self):
        return self.output_tokens_num_this_turn

    def get_history_input_tokens_num(self):
        return self.history_input_tokens_num

    def get_history_output_tokens_num(self):
        return self.history_output_tokens_num

    def _vllm_api_get_token_num(self, query):
        # 1. 定义 API 端点和请求头
        # dyellow(f'url={self.url!r}')

        # "https://powerai.cc:8001/v1"改为"https://powerai.cc:8001/tokenize"
        # 定义匹配模式
        pattern = r"^(.*?)/v1$"
        # ^       -> 匹配字符串的开始
        # (.*?)   -> 非贪婪地捕获所有字符，直到下一个模式。这是捕获组1
        # /v1     -> 匹配字面上的 /v1
        # $       -> 匹配字符串的结尾

        # 定义替换格式
        # \1 代表在 pattern 中捕获的第一个组的内容
        replacement = r"\1/tokenize"

        # 执行替换
        # re.sub 如果找不到匹配，会原样返回字符串
        new_url, count = re.subn(pattern, replacement, self.url)

        url = new_url
        headers = {
            "Content-Type": "application/json"
        }

        # 2. 准备要发送的数据 (payload)
        # 注意：在原始 curl 命令中，缺少 "model" 参数。
        # vLLM 的 /tokenize 接口通常需要模型名称。
        # 这里我们假设模型是 'default'，您可能需要根据实际情况修改。
        payload = {
            "prompt": query,
            "model": self.model_id  # <-- 如果需要，请取消此行注释并填入正确的模型名称
        }

        rtn_data = {
            'success': False,
            'count': 0,
            'max_model_len': 0
        }

        try:
            # 3. 发送 POST 请求
            # - requests.post() 发送 POST 请求
            # - url 是请求的目标地址
            # - headers 参数传递请求头
            # - json 参数会将 Python 字典自动转换为 JSON 字符串并设置正确的 Content-Type
            response = requests.post(url, headers=headers, json=payload)

            # 4. 检查响应状态码，确保请求成功 (200 OK)
            response.raise_for_status()  # 如果状态码不是 2xx，则会抛出异常

            # 5. 解析并打印 JSON 响应内容
            response_data = response.json()
            # print("请求成功！")
            # print("响应内容:")
            # 使用 json.dumps 美化输出
            # print(json.dumps(response_data, indent=2, ensure_ascii=False))

            # 单独提取 token 数量
            if "count" in response_data:
                # print(f"\nToken 数量: {response_data['count']}")

                rtn_data['success'] = True
                rtn_data['count'] = response_data['count']
                # dgreen(f"【LLM_Client】本次输入token数 : {rtn_data['count']}")
                if "max_model_len" in response_data:
                    rtn_data['max_model_len'] = response_data['max_model_len']
                    # dgreen(f"【LLM_Client】api的max_model_len : {rtn_data['max_model_len']}")

                # 刷新LLM_Client的历史token数量
                self.input_tokens_num_this_turn = response_data['count']
                if self.history:
                    self.history_input_tokens_num += response_data['count']
                    # dgreen(f"【LLM_Client】历史输入token数 : {self.history_input_tokens_num}")
                else:
                    self.history_input_tokens_num = response_data['count']
                    # dgreen(f"【LLM_Client】历史输入token数 : {self.history_input_tokens_num}")

        except Exception as e:
            # 如果响应不是有效的 JSON，则捕获错误
            dred(f'LLM_Client._vllm_api_get_token_num()报错：{e!r}')

        return rtn_data

    # 返回stream(generator)
    def ask_prepare(
            self,
            question,
            image_url=None,
            temperature=None,
            top_p=None,
            max_new_tokens=None,
            # in_top_p=None,
            clear_history=False,
            stream=True,
            retry=False,
            undo=False,
            stop=None,
            manual_stop=None,  # 用于vllm处理stop有bug
            # remove_content_in_think_pairs=False,        # remove ('<think>', '</think>') 之间的内容
            # think_pair=config.LLM_Default.think_pairs,
            system_prompt=None,
            role_prompt=None,
            audio_string=None,
    ):
        self._vllm_api_get_token_num(query=question)

        # self.temperature = config.LLM_Default.temperature if temperature is None else temperature
        self.max_new_tokens = config.LLM_Default.max_new_tokens if max_new_tokens is None else max_new_tokens
        clear_history = int(config.LLM_Default.clear_history if clear_history is None else clear_history)
        self.stream = int(config.LLM_Default.stream if stream is None else stream)
        # in_stop = config.LLM_Default.stop if in_stop is None else in_stop

        # 如果包含语音输入，则question直接改为语音对应的text
        if audio_string:
            self.audio_to_wav_file('temp_stt.wav', audio_string)
            question = self.audio_file_to_text('temp_stt.wav')
            dgreen(f'--------------------------语音输入已转为文本---------------------------------')
            dgreen(f'"{question}"')
            dgreen(f'-------------------------------------------------------------------------')

        if system_prompt is not None:
            self.set_system_prompt(system_prompt)
        if role_prompt is not None:
            self.set_role_prompt(role_prompt)

        # 如果输入image的path
        if image_url:
            image_url = get_image_string_from_url(image_url)

        dprint(f'{"-" * 40}输入参数{"-" * 40}')
        dprint(f'self.url: {self.url!r}')
        dprint(f'self.history: {self.history!r}')
        dprint(f'clear_history: {clear_history!r}')
        dprint(f'self.model_id: {self.model_id!r}')
        dprint(f'self.api_key: {self.api_key!r}')

        dprint(f'temperature: {temperature!r}')
        dprint(f'top_p: {top_p!r}')
        dprint(f'stream: {stream!r}')
        dprint(f'max_new_tokens: {max_new_tokens!r}')
        dprint(f'stop: {stop!r}')
        dprint(f'question: "【{question!r}】"')
        dprint(f'{"-" * 40}采用参数{"-" * 40}')

        if self.vpn_on:
            import httpx
            http_client = httpx.Client(
                proxy=config.g_vpn_proxy)
            self.openai = OpenAI(
                api_key=self.api_key,
                base_url=self.url,
                http_client=http_client,
                # http_client=openai.DefaultHttpxClient(verify=False),  # 用于自建的vllm openai api的ssl访问(https访问)， # 阿里云购买了正式证书（可以是免费的）后，即可开启verify，也就是去掉本行
            )
        else:
            self.openai = OpenAI(
                api_key=self.api_key,
                base_url=self.url,
                # http_client=openai.DefaultHttpxClient(verify=False),  # 用于自建的vllm openai api的ssl访问(https访问)， # 阿里云购买了正式证书（可以是免费的）后，即可开启verify，也就是去掉本行
            )
        try:
            if self.model_id is None or self.model_id == '':
                # print('------------------------------1--------------------------')
                old_model_id = self.model_id
                # print('------------------------------2--------------------------')
                # print(self.openai.models)
                # print(self.openai.models.list())
                # print('------------------------------2.1--------------------------')
                self.model_id = self.openai.models.list().data[0].id
                # print('------------------------------3--------------------------')
                dblue(f'【LLM_Client】change model_id from "{old_model_id}" to "{self.model_id}"\n')
        except Exception as e:
            # print('------------------------------4--------------------------')
            print(f'【LLM_Client异常】ask_prepare(): "{e}"')
            print(f'【LLM_Client异常】ask_prepare(): 可能是IP或Port设置错误，当前url为: {self.url}')
            self.model_id = 'wrong'
            # print('------------------------------5--------------------------')

        self.usage = None  # 清空输入和输出的token数量统计

        if not max_new_tokens:
            max_new_tokens = self.max_new_tokens
        else:
            max_new_tokens = max_new_tokens
        self.response_canceled = False
        # self.__history_add_last_turn_msg()

        if clear_history:
            self.__history_clear()

        if type(question) == str:
            # 输入仅为question字符串
            msgs = self.__history_messages_with_system_and_new_question(question=question, image_url=image_url)
        elif type(question) == list:
            # 输入为history list([{"role": "user", "content":'xxx'}, ...])
            msgs = question
        else:
            raise Exception(
                'LLM_Client.ask_prepare(): question格式错误，必须是str或[{"role": "user", "content":"xxx"}, ...]这样的list')

        # ==========================================================
        # print('发送到LLM的完整提示: ', msgs)
        # print(f'------------------------------------------------------------------------------------------')
        if temperature is None:
            run_temperature = self.temperature
        else:
            run_temperature = temperature

        if top_p is None:
            run_top_p = self.top_p
        else:
            run_top_p = top_p

        if self.print_input:
            if image_url is None:
                # question为文本
                dgreen('<User>', end='', flush=True)
                print(msgs[-1]['content'], end='', flush=True)
                dgreen(f'</User>(temperature={run_temperature}, top_p={run_top_p}, {self.input_tokens_num_this_turn}/{self.history_input_tokens_num}tokens)')
                # dgreen(f'</User>(temperature={run_temperature}, think关键字=("{self.think_pair[0]}", "{self.think_pair[1]}"))')
            else:
                # question为文本和图片
                dgreen('<User>', end='', flush=True)
                print(msgs[-1]['content'][0]['text'], end='', flush=True)
                dgreen(f'</User>(temperature={run_temperature}, top_p={run_top_p}, {self.input_tokens_num_this_turn}/{self.history_input_tokens_num}tokens with image.)')
                # dgreen(f'</User>(temperature={run_temperature}, think关键字=("{self.think_pair[0]}", "{self.think_pair[1]}"), with image.)')

        if stop is None:
            # stop = ['<|im_end|>', '<|im_start|>']
            # stop = ['<|im_end|>', '<|im_start|>', 'assistant', 'Assistant', '<step>']
            # stop = ['<|im_end|>', '<|im_start|>', '<s>', '</s>', 'human', 'Human', 'assistant', 'Assistant', '<step>']
            stop = None
        else:
            # stop = ['<|im_end|>', '<|im_start|>'] + in_stop
            # stop = ['<|im_end|>', '<|im_start|>', 'assistant', 'Assistant', '<step>'] + in_stop
            # stop = ['<|im_end|>', '<|im_start|>', '<s>', '</s>', 'human', 'Human', 'assistant', 'Assistant', '<step>'] + in_stop
            stop = stop

        self.stop = stop
        self.manual_stop = manual_stop

        dprint(f'{"-" * 80}')
        # dprint(f'self.openai: {self.openai}')
        dprint(f'self.model_id: {self.model_id!r}')
        dprint(f'run_temperature: {run_temperature!r}')
        dprint(f'run_top_p: {run_top_p!r}')
        dprint(f'stream: {stream!r}')
        dprint(f'max_tokens: {max_new_tokens!r}')
        dprint(f'stop: {stop!r}')
        dprint(f'messages: {msgs!r}')

        self.status.question = question
        self.status.model_id = self.model_id
        self.status.temperature = run_temperature
        self.status.max_new_tokens = max_new_tokens
        self.status.stops = stop
        self.status.system_prompt = self.system_prompt
        status_to_redis(self.status)

        try:
            if self.reasoning_effort is not None:
                gen = self.openai.chat.completions.create(
                    model=self.model_id,
                    temperature=run_temperature,
                    top_p=run_top_p,
                    # top_k=self.top_k,
                    # top_p = run_top_p,
                    # system=self.role_prompt if self.has_role_prompt else "You are a helpful assistant.",  # vllm目前不支持qwen的system这个参数
                    messages=msgs,
                    stream=stream,
                    # max_new_tokens=max_new_tokens,   # 目前openai_api未实现（应该是靠models下的配置参数指定）
                    max_tokens=max_new_tokens,  # 目前openai_api未实现（应该是靠models下的配置参数指定）
                    stop=stop,
                    # stop_token_ids=[151329, 151336, 151338],    # glm9b-chat-1m
                    # Specifying stop words in streaming output format is not yet supported and is under development.

                    stream_options={"include_usage": True},  # 最新版本openai的要求
                    extra_body={'reasoning_effort':self.reasoning_effort}
                    # top_p=0.95,   # 防止过度重复
                    # top_k=40,     # 复杂数学或代码
                    # top_k=20,     # 其他类型问题
                )
            else:
                gen = self.openai.chat.completions.create(
                    model=self.model_id,
                    temperature=run_temperature,
                    top_p=run_top_p,
                    # top_k=self.top_k,
                    # top_p = run_top_p,
                    # system=self.role_prompt if self.has_role_prompt else "You are a helpful assistant.",  # vllm目前不支持qwen的system这个参数
                    messages=msgs,
                    stream=stream,
                    # max_new_tokens=max_new_tokens,   # 目前openai_api未实现（应该是靠models下的配置参数指定）
                    max_tokens=max_new_tokens,  # 目前openai_api未实现（应该是靠models下的配置参数指定）
                    stop=stop,
                    # stop_token_ids=[151329, 151336, 151338],    # glm9b-chat-1m
                    # Specifying stop words in streaming output format is not yet supported and is under development.

                    stream_options={"include_usage": True},  # 最新版本openai的要求
                    # top_p=0.95,   # 防止过度重复
                    # top_k=40,     # 复杂数学或代码
                    # top_k=20,     # 其他类型问题
                )

            dprint(f'===self.openai.chat.completions.create() invoked.===')
            dprint(f'{"-" * 80}')
        except Exception as e:
            dred(f'【LLM_Client异常】ask_prepare(): {e!r}(注意：api_key不能设置为"")')
            self.question_last_turn = question
            return self

        self.gen = gen

        self.question_last_turn = question
        return self

    def set_thinking_stream_buf(self, output_stream_buf):
        self.thinking_stream_buf = output_stream_buf

    def set_result_stream_buf(self, result_stream_buf):
        self.result_stream_buf = result_stream_buf

    def thinking_stream(self, chunk):
        # if self.thinking_stream_buf:
        #     self.thinking_stream_buf(chunk)
        pass

    def result_stream(self, chunk):
        # if self.result_stream_buf:
        #     self.result_stream_buf(chunk)
        pass

    def get_think_generator(self):
        think_started = False
        for chunk in self.get_answer_generator():
            full_chunk = chunk[0]
            think_chunk = chunk[1]
            result_chunk = chunk[2]
            if result_chunk:
                # 说明不是reason模型
                self.result_chunk_as_think_chunk = result_chunk
                return None
            if think_chunk:
                think_started = True
                self.thinking_stream(think_chunk)
                yield think_chunk
            if (not think_chunk) and think_started:
                # 此时think内容结束，退出，便于后面获取result内容
                return None

    def get_result_generator(self):
        if self.result_chunk_as_think_chunk:
            # 把误将result_chunk当成think_chunk的chunk还给result
            yield self.result_chunk_as_think_chunk

        for chunk in self.get_answer_generator():
            full_chunk = chunk[0]
            think_chunk = chunk[1]
            result_chunk = chunk[2]
            # self.result_stream(result_chunk)
            yield result_chunk

    def get_answer_and_sync_print(self):
        full = ''
        think = ''
        result = ''

        # for chunk in self.get_answer_generator():
        #     print(chunk, flush=True)

        think_started = False
        result_started = False
        for chunk in self.get_answer_generator():
            # 需要过滤think内容
            full += chunk[0]
            think += chunk[1]
            result += chunk[2]
            # print(f'think: "{think}"')
            if chunk[1]:
                if not think_started:
                    dyellow('<think>')
                print(chunk[1], end='', flush=True)
                think_started = True
            if chunk[2]:
                if not result_started:
                    if think_started:
                        dyellow('</think>')
                    dblue('<assistant>', end='', flush=True)
                print(chunk[2], end='', flush=True)
                result_started = True
        dblue(f'</assistant>({self.output_tokens_num_this_turn}/{self.history_output_tokens_num}tokens)')

        return result

    # 方式2：返回generator，在合适的时候输出结果
    # chunk[0] 原始full chunk
    # chunk[1] think chunk
    # chunk[2] result chunk
    # def legacy_get_answer_generator(self):
    #     answer = ''
    #     answer_no_partial_stop = ''
    #     perhaps_stop_string = ''    # 非常重要，用于存放疑似stop的缓冲
    #
    #
    #     answer_no_partial_think_pair = ''
    #     perhaps_think_pair_string = ''     # 非常重要，用于存放疑似think的缓冲
    #     thinking_content = ''
    #     last_thinking_content = ''
    #
    #     result_content = ''
    #     last_result_content = ''
    #
    #     try:
    #         # dprint(f'self.gen: {self.gen}')
    #         for chunk in self.gen:
    #             # dprint(f'chunk: {chunk}')
    #             if self.response_canceled:
    #                 break
    #
    #             # print(f'chunk.choices[0].delta: {chunk.choices[0].delta}')
    #             # print(f'chunk: {chunk}')
    #             if hasattr(chunk, 'usage') and chunk.usage is not None:
    #                 self.usage = {}
    #                 self.usage['prompt_tokens'] = chunk.usage.prompt_tokens
    #                 self.usage['total_tokens'] = chunk.usage.total_tokens
    #                 self.usage['completion_tokens'] = chunk.usage.completion_tokens
    #
    #             if chunk.choices and hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
    #                 # if hasattr(chunk, 'usage') and chunk.usage is not None:
    #                 #     print(f'chunk.usage: {chunk.usage}')
    #                 #     # 输入和输出的token数量统计
    #                 #     # dred(f'usage = {chunk.usage}')
    #                 #     # dred(f'type(usage) = {type(chunk.usage)}')
    #                 #     if type(chunk.usage) is openai.types.completion_usage.CompletionUsage:
    #                 #         # deepseek API采用openai.types.completion_usage.CompletionUsage: CompletionUsage(completion_tokens=50, prompt_tokens=18, total_tokens=68)
    #                 #         self.usage = {}
    #                 #         self.usage['prompt_tokens'] = chunk.usage.prompt_tokens
    #                 #         self.usage['total_tokens'] = chunk.usage.total_tokens
    #                 #         self.usage['completion_tokens'] = chunk.usage.completion_tokens
    #                 #     else:
    #                 #         # vllm API采用: {'prompt_tokens': 21, 'total_tokens': 38, 'completion_tokens': 17}
    #                 #         self.usage = chunk.usage
    #
    #                 my_chunk = chunk.choices[0].delta.content
    #                 answer += my_chunk
    #
    #                 chunk_output = ''
    #                 think_chunk_output = ''
    #                 result_chunk_output = ''
    #
    #                 # ----------------------------------1、判断是否有('<think>', '</think>')这样的think pair需要过滤----------------------------------------
    #                 if True:
    #                 # if self.remove_content_in_think_pairs:
    #                     # ----------------------------------需要过滤('<think>', '</think>')之间内容----------------------------------
    #                     answer_no_partial_think_pair = str_remove_content_in_partial_pairs(answer, self.think_pair)
    #                     if answer_no_partial_think_pair == answer:
    #                         # ----------------------------------没有('<think>', '</think>')----------------------------------
    #                         result_chunk_output = my_chunk
    #                         # pass
    #                     else:
    #                         # ----------------------------------有('<think>', '</think>')----------------------------------
    #                         if self.think_pair[1] not in answer:
    #                             # 如果 '</think>' not in answer，也就是还没有输出结论
    #                             thinking_content = _str_get_content_in_partial_pairs(answer, self.think_pair)
    #                             think_chunk_output = thinking_content.replace(last_thinking_content, '', 1)    # 只去掉最左边的last_thinking_content
    #                             last_thinking_content = thinking_content
    #                         else:
    #                             # 如果 '</think>' in answer，也就是开始输出结论
    #                             think_chunk_output = ''
    #
    #
    #                             # 处理result
    #                             result_content = str_remove_content_in_partial_pairs(answer, self.think_pair)
    #
    #                             # print(f'\n-----------answer------------\n"{answer}"')
    #                             # print(f'--------------------------------------------')
    #                             # print(f'\n-----------result_content------------\n"{result_content}"')
    #                             # print(f'--------------------------------------------')
    #                             # print(f'\n-----------last_result_content------------\n"{last_result_content}"')
    #                             # print(f'--------------------------------------------')
    #
    #                             result_chunk_output = result_content.replace(last_result_content, '', 1)  # 只去掉最左边的last_thinking_content
    #                             last_result_content = result_content
    #                             # print(f'\n-----------result_chunk_output------------\n"{result_chunk_output}"')
    #                             # print(f'--------------------------------------------')
    #
    #                         # print(f'\n-------------think_chunk_output-------------\n"{think_chunk_output}"')
    #                         # print(f'--------------------------------------------')
    #                 else:
    #                     # ----------------------------------不需要过滤('<think>', '</think>')之间内容----------------------------------
    #                     pass
    #
    #                 # ----------------------------------2、判断是否有['[观察]']这样的stop----------------------------------------
    #                 answer_for_stop = ''
    #                 chunk_for_stop = ''
    #                 result_chunk_after_stop = ''
    #
    #                 answer_for_stop = result_chunk_output
    #                 chunk_for_stop = result_chunk_output
    #                 # if self.remove_content_in_think_pairs:
    #                 #     answer_for_stop = result_chunk_output
    #                 #     chunk_for_stop = result_chunk_output
    #                 # else:
    #                 #     answer_for_stop = answer
    #                 #     chunk_for_stop = my_chunk
    #
    #                 if self.stop:
    #                     # 进行stop的增强修正(vllm的stop机制有bug，有时agent中的特殊stop如"观察"无法正确停止)
    #                     answer_no_partial_stop = str_remove_partial_substring_or_right(answer_for_stop, self.stop)
    #                     # answer_no_partial_stop = str_remove_partial_substring(answer, self.stop)
    #
    #                     # print(f'answer1: {answer}')
    #                     # print(f'answer2: {answer_no_partial_stop}')
    #                     if answer_no_partial_stop == answer_for_stop:
    #                     # if answer_no_partial_stop == answer:
    #                         # ----------------------------------不是stop标识----------------------------------
    #                         my_chunk = perhaps_stop_string + my_chunk   # 1、将证实不是stop的字符补在前面
    #                         perhaps_stop_string = ''                    # 2、清空疑似stop的缓冲
    #                         # 没partial_stop
    #                         # print(my_chunk, end='', flush=True)
    #
    #                         # yield my_chunk
    #
    #                         result_chunk_after_stop = chunk_for_stop
    #                         # chunk_output = my_chunk
    #                     else:
    #                         # ----------------------------------是stop标识----------------------------------
    #                         # dred(f'===================================================')
    #                         # dred(f'-------------遇到stop标识: {self.stop}---------------')
    #                         # dred(f'-------------answer_no_partial_stop: "{answer_no_partial_stop[-20:]}"---------------')
    #                         # dred(f'-------------answer_for_stop: "{answer_for_stop[-20:]}"---------------')
    #                         # dred(f'===================================================')
    #                         perhaps_stop_string += chunk_for_stop #存放疑似stop的缓冲，后面如果证实不是stop，需要补回去
    #                         # perhaps_stop_string += my_chunk #存放疑似stop的缓冲，后面如果证实不是stop，需要补回去
    #
    #                         # 有partial_stop
    #                         # print(f'*{my_chunk}*', end='', flush=True)
    #
    #                         # yield ''
    #
    #                         result_chunk_after_stop = ''
    #                         # chunk_output = ''
    #                 else:
    #                     # ----------------------------------没有stop----------------------------------
    #                     # yield my_chunk
    #
    #                     result_chunk_after_stop = chunk_for_stop
    #                     # chunk_output = my_chunk
    #
    #                 yield my_chunk, think_chunk_output, result_chunk_after_stop
    #                 # if self.remove_content_in_think_pairs:
    #                 #     # 过滤think内容
    #                 #     yield my_chunk, think_chunk_output, result_chunk_after_stop
    #                 #     # yield chunk_output, think_chunk_output, result_chunk_output
    #                 # else:
    #                 #     # 不过滤think内容
    #                 #     yield result_chunk_after_stop
    #                 #     # yield chunk_output
    #
    #     except Exception as e:
    #         dred(f'LLM_Client("{self.url}")连接异常: {e}')
    #         yield '', '', ''
    #         # if self.remove_content_in_think_pairs:
    #         #     # 过滤think内容
    #         #     yield '', '', ''
    #         # else:
    #         #     # 不过滤think内容
    #         #     yield ''
    #
    #     if self.stop:
    #         self.answer_last_turn = answer_no_partial_stop
    #     else:
    #         self.answer_last_turn = answer
    #
    #     self.answer_last_turn = str_remove_content_in_partial_pairs(self.answer_last_turn, self.think_pair)
    #     # if self.remove_content_in_think_pairs:
    #     #     # print(f'\n-----------------last1-----------------\n"{self.answer_last_turn}"')
    #     #     self.answer_last_turn = str_remove_content_in_partial_pairs(self.answer_last_turn, self.think_pair)
    #     #     # print(f'-----------------last2-----------------\n"{self.answer_last_turn}"')
    #     #     # print(f'---------------------------------------')
    #     # else:
    #     #     pass
    #
    #     # self.answer_last_turn = answer
    #     self.__history_add_last_turn_msg()
    #     # self.print_history_and_system()
    #
    #     self.status.last_response = answer
    #     self.status.history_list = self.history_list
    #     # dred(f'--------------self.last_response: {answer}')
    #     # dred(f'--------------self.history_list: {self.history_list}')
    #     # dred(f'--------------status: {self.status}')
    #     status_to_redis(self.status)

    # chunk[0] 原始full chunk
    # chunk[1] think chunk
    # chunk[2] result chunk
    def get_answer_generator(self):
        answer = ''
        answer_no_partial_stop = ''
        perhaps_stop_string = ''  # 非常重要，用于存放疑似stop的缓冲

        answer_no_partial_think_pair = ''
        perhaps_think_pair_string = ''  # 非常重要，用于存放疑似think的缓冲
        thinking_content = ''
        last_thinking_content = ''

        result_content = ''
        last_result_content = ''

        answer_for_stop = ''
        chunk_for_stop = ''
        result_chunk_after_stop = ''

        # thinking_model_has_no_start_thinking_first = True

        try:
            # dprint(f'self.gen: {self.gen}')
            for chunk in self.gen:
                # dprint(f'chunk: {chunk}')
                if self.response_canceled:
                    break

                # if 'hink' in self.model_id and thinking_model_has_no_start_thinking_first:
                #     thinking_model_has_no_start_thinking_first = False
                    # chunk = '<think>'

                chunk_output = ''
                think_chunk_output = ''
                result_chunk_output = ''

                # print(f'chunk.choices[0].delta: {chunk.choices[0].delta}')
                # print(f'chunk: {chunk}')
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    self.usage = {}
                    self.usage['prompt_tokens'] = chunk.usage.prompt_tokens
                    self.usage['total_tokens'] = chunk.usage.total_tokens
                    self.usage['completion_tokens'] = chunk.usage.completion_tokens

                    self.output_tokens_num_this_turn = self.usage['completion_tokens']
                    if self.history:
                        self.history_output_tokens_num += self.usage['completion_tokens']
                    else:
                        self.history_output_tokens_num = self.usage['completion_tokens']


                # if chunk.choices:
                #     print(chunk.choices[0].delta)

                # ================================================reasoning_content===================================================
                if chunk.choices and hasattr(chunk.choices[0].delta, "reasoning_content") and chunk.choices[
                    0].delta.reasoning_content:
                    think_chunk_output = chunk.choices[0].delta.reasoning_content
                    # print(f'think_chunk_output: "{think_chunk_output}"')

                    my_chunk = think_chunk_output
                    result_chunk_after_stop = ''

                    # 如果是think_chunk，直接返回，因为和stop无关
                    yield my_chunk, think_chunk_output, result_chunk_after_stop

                # =====================================================content========================================================
                if chunk.choices and hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content:
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

                    # print(chunk.choices[0].delta.content, end='', flush=True)
                    my_chunk = chunk.choices[0].delta.content
                    answer += my_chunk

                    # result_chunk_output = my_chunk

                    # ----------------------------------2、判断是否有['[观察]']这样的stop----------------------------------------

                    answer_for_stop += my_chunk
                    chunk_for_stop = my_chunk
                    # if self.remove_content_in_think_pairs:
                    #     answer_for_stop = result_chunk_output
                    #     chunk_for_stop = result_chunk_output
                    # else:
                    #     answer_for_stop = answer
                    #     chunk_for_stop = my_chunk
                    # dred(f'my_chunk: "{my_chunk}"')

                    if self.manual_stop:
                        # if self.stop:
                        # 进行stop的增强修正(vllm的stop机制有bug，有时agent中的特殊stop如"观察"无法正确停止)

                        for stop_string in self.manual_stop:
                            # 如果answer包含stop，退出
                            if stop_string in answer:
                                # dyellow(f'【stop】遇到stop标识"{stop_string}"，返回，answer="{answer}"')
                                return my_chunk, think_chunk_output, result_chunk_after_stop

                        # answer_no_partial_stop = str_remove_partial_substring_or_right(answer_for_stop, ['[观察]'])
                        answer_no_partial_stop = str_remove_partial_substring_or_right(answer_for_stop,
                                                                                       self.manual_stop)

                        # answer_no_partial_stop = str_remove_partial_substring(answer, self.stop)

                        # print(f'answer_for_stop: "{answer_for_stop}"', flush=True)
                        # print(f'answer_no_partial_stop: "{answer_no_partial_stop}"', flush=True)
                        if answer_no_partial_stop == answer_for_stop:
                            # if answer_no_partial_stop == answer:
                            # ----------------------------------不是stop标识----------------------------------
                            my_chunk = perhaps_stop_string + my_chunk  # 1、将证实不是stop的字符补在前面
                            perhaps_stop_string = ''  # 2、清空疑似stop的缓冲
                            # 没partial_stop
                            # print(my_chunk, end='', flush=True)

                            # yield my_chunk

                            # ===============！！！待测试！！！========================
                            result_chunk_after_stop = my_chunk
                            # result_chunk_after_stop = chunk_for_stop
                            # ===============！！！待测试！！！========================
                            # chunk_output = my_chunk
                        else:
                            # ----------------------------------是stop标识----------------------------------
                            # dred(f'===================================================')
                            # dred(f'-------------遇到stop标识: {self.stop}---------------')
                            # dred(f'-------------answer_no_partial_stop: "{answer_no_partial_stop[-20:]}"---------------')
                            # dred(f'-------------answer_for_stop: "{answer_for_stop[-20:]}"---------------')
                            # dred(f'===================================================')
                            perhaps_stop_string += chunk_for_stop  # 存放疑似stop的缓冲，后面如果证实不是stop，需要补回去
                            # print(f'chunk_for_stop: "{chunk_for_stop}"', flush=True)
                            # print(f'perhaps_stop_string: "{perhaps_stop_string}"', flush=True)

                            # perhaps_stop_string += my_chunk #存放疑似stop的缓冲，后面如果证实不是stop，需要补回去

                            # 有partial_stop
                            # print(f'*{my_chunk}*', end='', flush=True)

                            # yield ''

                            result_chunk_after_stop = ''
                            # chunk_output = ''

                            # yield my_chunk, think_chunk_output, result_chunk_after_stop
                    else:
                        # ----------------------------------没有stop----------------------------------
                        # yield my_chunk

                        result_chunk_after_stop = chunk_for_stop
                        # chunk_output = my_chunk

                    # print(f'result_chunk_after_stop: "{result_chunk_after_stop}"')
                    # print(f'my_chunk: "{my_chunk}"')
                    yield my_chunk, think_chunk_output, result_chunk_after_stop
                    # if self.remove_content_in_think_pairs:
                    #     # 过滤think内容
                    #     yield my_chunk, think_chunk_output, result_chunk_after_stop
                    #     # yield chunk_output, think_chunk_output, result_chunk_output
                    # else:
                    #     # 不过滤think内容
                    #     yield result_chunk_after_stop
                    #     # yield chunk_output

        except Exception as e:
            dred(f'LLM_Client("{self.url}")连接异常: {e}')
            yield '', '', ''
            # if self.remove_content_in_think_pairs:
            #     # 过滤think内容
            #     yield '', '', ''
            # else:
            #     # 不过滤think内容
            #     yield ''

        if self.stop:
            self.answer_last_turn = answer_no_partial_stop
        else:
            self.answer_last_turn = answer

        # self.answer_last_turn = str_remove_content_in_partial_pairs(self.answer_last_turn, self.think_pair)

        # if self.remove_content_in_think_pairs:
        #     # print(f'\n-----------------last1-----------------\n"{self.answer_last_turn}"')
        #     self.answer_last_turn = str_remove_content_in_partial_pairs(self.answer_last_turn, self.think_pair)
        #     # print(f'-----------------last2-----------------\n"{self.answer_last_turn}"')
        #     # print(f'---------------------------------------')
        # else:
        #     pass

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
class Async_LLM(legacy_Web_Server_Base):
    def __init__(self,
                 question,
                 url=config.LLM_Default.url,
                 api_key=config.LLM_Default.api_key,
                 model_id=None,
                 temperature=config.LLM_Default.temperature,
                 top_p=config.LLM_Default.top_p,
                 role_prompt='',
                 extra_suffix='',
                 streamlit=False,
                 is_web_server=False,
                 ):
        self.llm = None
        self.stream_buf_callback = None
        self.task = None
        self.role_prompt = ''
        self.extra_suffix = ''
        self.final_response = ''
        self.run_in_streamlit = False

        self.complete = False

        self.flicker = None

        self.getting_chunk = False
        self.chunk = ''

        self.prompt = question
        self.temperature = temperature
        self.top_p = top_p
        self.api_key = api_key
        self.base_url = url
        self.model_id = model_id

        self.role_prompt = role_prompt
        self.extra_suffix = extra_suffix  # 输出的额外内容
        self.run_in_streamlit = streamlit
        self.is_web_server = is_web_server

        self.thinking_stream_buf = None
        self.result_stream_buf = None
        self.log_stream_buf = None
        self.tool_cliet_data_stream_buf = None

    def init(self):
        from utils.task import Flicker_Task

        self.complete = False

        self.llm = LLM_Client(
            history=True,
            print_input=False,
            temperature=self.temperature,
            top_p=self.top_p,
            url=self.base_url,
            api_key=self.api_key,
            model_id=self.model_id
        )
        self.llm.set_role_prompt(self.role_prompt)
        self.flicker = Flicker_Task()

    def set_stream_result(self, result_output_func):
        self.result_stream_buf = result_output_func

    def set_stream_thinking(self, thinking_output_func):
        self.thinking_stream_buf = thinking_output_func  # 最终结果stream输出的的func

    def set_stream_log(self, log_output_func):
        self.log_stream_buf = log_output_func  # 最终结果stream输出的的func

    # 暂时没用，主要用于tool_agent
    def set_stream_tool_result_data(self, tool_result_data_output_func):
        self.tool_client_data_stream_buf = tool_result_data_output_func  # 最终结果stream输出的的func

    def get_final_response(self):
        return self.final_response

    def wait(self):
        if self.task:
            self.task.join()

    # 如果is_web_server，async llm对数据chunk进行格式化
    # 格式化后的chunk = {'type':Web_Client_Data_Type.TEXT, 'data':{'content':,...}}
    def result_stream(self, chunk):
        if self.result_stream_buf:
            if self.is_web_server:
                text_data = Web_Client_Text_Data(
                    content=chunk,
                    font='宋体, SimSun',
                    size='12',
                    color='black'
                )
                client_data = Web_Client_Data(type=Web_Client_Data_Type.TEXT, data=text_data)
                client_data_str = json.dumps(asdict(client_data), ensure_ascii=False)
                self.result_stream_buf(client_data_str)

            else:
                self.result_stream_buf(chunk)

    def run(self):
        # print(f'【Async_LLM】run(temperature={self.temperature}) invoked.')
        gen = self.llm.ask_prepare(self.prompt).get_result_generator()
        # gen = self.llm.ask_prepare(self.prompt).get_answer_generator()
        full_response = ''

        # 将for chunk in gen的同步next(gen)改造为异步，从而在stream暂时没有数据时，从而让光标闪烁等事件能够被响应。
        self.chunk = ''
        self.getting_chunk = False
        while not self.complete:
            def get_chunk():
                if not self.getting_chunk:
                    self.getting_chunk = True
                    try:
                        self.chunk = next(gen)
                        self.result_stream(self.chunk)
                    except StopIteration as e:
                        self.complete = True
                    self.getting_chunk = False

            if not self.getting_chunk:
                full_response += self.chunk
                self.final_response = full_response
                t = threading.Thread(target=get_chunk)
                t.start()
                # chunk = next(gen)

            if self.stream_buf_callback:
                self.stream_buf_callback(full_response + self.flicker.get_flicker())
            # time.sleep(0.05)

        # 注意：vllm并行query刚开始时，这行代码这里会卡死2-3秒钟。因此需要改造为异步，从而让光标闪烁等事件能够被响应。
        # for chunk in gen:
        #     full_response += chunk
        #     self.stream_buf_callback(full_response + self.flicker.get_flicker())

        # print(f'【Async_LLM】extra_suffix= {self.extra_suffix}')
        full_response += self.extra_suffix
        if self.stream_buf_callback:
            self.stream_buf_callback(full_response)

        self.final_response = full_response

        dprint(
            f'【Async_LLM】run() completed. temperature={self.temperature}, top_p={self.top_p}, final_response="{self.final_response}"')

    def start(self):
        # 由于streamlit对thread支持不好，这里必须在threading.Thread(target=self.run)之后紧跟调用add_script_run_ctx(t)才能正常调用run()里面的st.markdown()这类功能，不然会报错：missing xxxxContext
        self.task = threading.Thread(target=self.run)
        if self.run_in_streamlit:
            from streamlit.runtime.scriptrunner import add_script_run_ctx
            add_script_run_ctx(self.task)

        self.task.start()
        self.flicker.init(flicker1='█ ', flicker2='  ').run()

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
        new_loop.run_until_complete(self.task)  # 改行是阻塞等待task完成
        dprint(f'Async_LLM.start() invoked.')


# 通过多个llm的client，对model进行并发访问，同步返回多个stream
class Concurrent_LLMs:
    def __init__(self, in_url=config.LLM_Default.url):
        # def __init__(self, in_url='http://127.0.0.1:8001/v1/'):
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
            in_prompts,  # 输入的多个prompt
            in_contents,  # 输入的多个长文本(需要分别嵌入prompt进行解读)
            in_stream_buf_callbacks=None,  # 用于执行stream输出的回调函数list(该回调函数list可以是[streamlit.empty[].markdown, ...])
            in_role_prompts=None,  # 输入的多个role prompt
            in_extra_suffixes=None,  # 输出的额外内容(维度同上)
            in_cursor='█ ',  # 输出未完成时显示用的光标
            in_max_new_tokens=2048,
            in_content_short_enough=True,  # 如果short_enough, 则每个qa只需要调用short_content_qa而不用调用long_content_qa(分段)
    ):
        from tools.qa.long_content_qa import short_content_qa, long_content_qa_concurrently

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
            self.llms.append(
                LLM_Client(history=False, max_new_tokens=in_max_new_tokens, print_input=False, temperature=0,
                           url=self.url))
            self.llms_post_processed.append(False)
        self.llms_num = len(self.llms)

        self.flicker = Flicker_Task()
        self.flicker.init(flicker1='█ ', flicker2='  ').run()

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
            'type': 'running',
            'canceled': False,
            'describe': '启动解读任务...',
            'detail': f'所有llm已完成初始化，llm数量为{llm_num}.',
            'llms_complete': [False] * llm_num,
            'llms_full_responses': [''] * llm_num,
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
                    if i == 0:
                        dprint(chunk, end='')

                except StopIteration as e:
                    # 如果next引发StopIteration异常，则设置finished为True
                    status['llms_complete'][i] = True
                except Exception as e:
                    print(f'llm[{i}] next(gen) error: "{e}"')
                    status['llms_full_responses'][i] = '服务器错误: llm输入长度超限.'
                    status['llms_complete'][i] = True

                # 向外部stream接口输出当前llm的stream chunk
                if status['llms_complete'][i]:
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
                    if len(status['llms_full_responses'][i]) > 5:
                        # print('self.stream_buf_callbacks:', self.stream_buf_callbacks)
                        if self.stream_buf_callbacks:
                            self.stream_buf_callbacks[i](
                                status['llms_full_responses'][i] + self.flicker.get_flicker() + '\n\n')
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
        llm.ask_prepare(query, max_new_tokens=500).get_answer_and_sync_print()


def pic_main():
    import os

    llm = LLM_Client(
        temperature=0.6,
        url='http://powerai.cc:28001/v1/'
    )

    cwd = os.getcwd()
    print("当前工作目录是：", cwd)
    pic_name = '110kV沈家湾变主接线图.jpg'
    pic_path = cwd + '/' + pic_name
    # pic_path = cwd + '\\' + pic_name

    llm.ask_prepare(
        question='图中的黄色母线的电压等级是多少？黄色母线上有多少出线，各个出线的名称是什么？',
        image_url=pic_path,
        max_new_tokens=1024,
    ).get_answer_and_sync_print()
    # -----------------------------------2025-04-21: gpt-o4-mini-high(多模态推理模型)的回答-----------------------------------
    # 黄色母线就是图中用黄色画出的 35kV 母线。沿这条母线共有 5 条真正的出线（不含分段刀闸和母线分段开关），它们按母线分段情况可分布为：
    #
    # 35kV I 段母线（最左侧黄色母线段）
    # 沈大（馈线）
    # ＃1电抗器
    # 35kV II 段乙母线（最右侧黄色母线段）
    # 3. 基沈（馈线）
    # 4. 沈洋（馈线）
    # 5. ＃2电抗器
    # （中间的母线分段开关和“35kV I、II 段母分”都只用来分段或联络，不算出线。）
    # ----------------------------------/gpt-o4-mini-high(多模态推理模型)的回答-----------------------------------

    llm.ask_prepare('我刚才问你什么了？', max_new_tokens=1024).get_answer_and_sync_print()


def main2():
    llm = LLM_Client(
        api_key='empty',
        url='https://powerai.cc:8001/v1',

        # api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        # url='https://api.deepseek.com/v1',

        # history=True,
        # history_max_turns=50,
        # history_clear_method='pop',
        # temperature=0.7,
        # # url='https://192.168.124.33:8001/v1/'
        #
        # # 测试https（阿里云购买的免费ssl证书，绑定在powerai.cc）
        # # url='https://172.27.67.106:8001/v1/'  # 不通
        # # url='https://116.62.63.204:8001/v1/'  # 不通
        # url='https://powerai.cc:8001/v1/'     # 通过
        # # url='https://localhost:8001/v1/'      # 不通
    )
    # print('models: ', openai.models.list().data)
    # llm.set_system_prompt('不管我说什么，都直接把我说的话翻译为中文回复给我.')
    # llm.set_role_prompt('不管我说什么，都直接把我说的话翻译为中文回复给我.')

    # gen  = llm.ask_prepare('你是谁？我的名字是土土', temperature=0.5, max_new_tokens=200).get_answer_generator()
    # for chunk in gen:
    #     print(chunk, end='', flush=True)

    llm.ask_with_prm('你是谁？我叫土土', temperature=0.5, max_new_tokens=200).get_answer_and_sync_print()
    llm.ask_with_prm('我刚才告诉你我的名字是什么？', temperature=0.5, max_new_tokens=200).get_answer_and_sync_print()
    # llm.ask_prepare('你还记得我的名字吗', temperature=0.5, max_new_tokens=200).get_answer_and_sync_print()
    # llm.ask_prepare('write a word', in_temperature=0.6, in_max_new_tokens=300).get_answer_and_sync_print()
    # llm.ask_prepare('write 3 words', in_temperature=0.9, in_stop=['<s>', '|<end>|'], in_max_new_tokens=400).get_answer_and_sync_print()


# 控制台并发stream的测试
def _console_asks(stdscr, prompt, temperature, max_new_tokens):
    from tools.llm.api_prm_client import LLM_PRM_Client, Step_Data
    prm = LLM_PRM_Client()
    prm.init()

    def _user_callback(win_data):
        thread_id = win_data.thread_id
        output = win_data.output_buf
        win_obj = win_data.win_obj

        llm = LLM_Client(
            api_key='empty',
            url='https://powerai.cc:8001/v1',
            # api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
            # url='https://api.deepseek.com/v1',
        )

        # gen = llm.ask_prepare('写一首长诗', temperature=temperature, max_new_tokens=1000).get_answer_generator()
        gen = llm.ask_prepare(question=prompt, temperature=temperature,
                              max_new_tokens=max_new_tokens).get_answer_generator()
        # gen = llm.ask_prepare('选取一首李白的诗，将诗的名字返回给我', temperature=temperature, max_new_tokens=200).get_answer_generator()

        res = ''
        caption = f' temperature={temperature:.1f}'
        for chunk in gen:
            res += chunk
            output(content=res, caption=caption)

        # 获取step_rewards
        step_data = Step_Data(problem=prompt, response=res)
        step_rewards = prm.get_step_rewards(step_data)

        # 输出step_rewards信息
        rewards_list = [f'{r:.2f}' for r in step_rewards]
        res += f'[{",".join(rewards_list)}]'
        output(content=res, caption=caption)

        # while True:
        #     content = f'这是window[{win_obj.thread_id}], 时间: {time.strftime("%H:%M:%S")}'
        #     win_obj.output_buf(content)
        #     time.sleep(0.1)

    from tools.console.windows import Console_Windows
    console = Console_Windows()
    console.init(stdscr=stdscr, user_callback=_user_callback)
    console.start()


# 通过PRM筛选并发采样结果
def ask_with_prm(question, llm_key='empty', prm_key='empty', llm_url='https://powerai.cc:8001/v1',
                 prm_url='https://powerai.cc:8002/v1',
                 max_new_tokens=1024, temperature=0.7, n=10,
                 prm_model_path='/home/tutu/models/Skywork-o1-Open-PRM-Qwen-2.5-7B'):
    from tools.llm.api_prm_client import LLM_PRM_Client, Step_Data
    prm = LLM_PRM_Client()
    prm.init(prm_model_path=prm_model_path, url=prm_url, api_key=prm_key)

    res_dict = {}

    dgreen(f'ask_with_prm()已启动，n_sample={n}')

    def _task(id):
        llm = LLM_Client(api_key=llm_key, url=llm_url)
        gen = llm.ask_prepare(question=question, temperature=temperature,
                              max_new_tokens=max_new_tokens).get_answer_generator()
        res = ''
        for chunk in gen:
            res += chunk

        # 获取step_rewards
        step_data = Step_Data(problem=question, response=res)
        step_rewards = prm.get_step_rewards(step_data)

        # 存储当前id下的response
        res_dict[id] = {
            'response': res,
            'step_rewards': step_rewards,
            'min_reward': prm.get_min_reward(),
            'last_reward': prm.get_last_reward(),
            'prod_reward': prm.get_prod_reward(),
        }

    # 启动callback任务
    threads = []
    for i in range(n):  # 有10个线程
        t = threading.Thread(target=_task, args=(i,))
        threads.append(t)
        t.start()

    # 等待所有任务完成
    for t in threads:
        t.join()

    # 显示每一个id下的response和step_rewards
    dgreen(f'ask_with_prm()完成，n_sample={n}')

    from utils.string_util import string_right_align
    for i in range(n):
        s = ' '.join(res_dict[i]['response'][-50:].split('\n'))
        rewards_list = [f'{r:.2f}' for r in res_dict[i]['step_rewards']]
        # s += f'【{",".join(rewards_list)}】'
        s += f'【min: {res_dict[i]["min_reward"]:.2f}】'
        s += f'【prod: {res_dict[i]["prod_reward"]:.9f}】'
        s += f'【last: {res_dict[i]["last_reward"]:.2f}】'
        print(f'[{i}]: "...{string_right_align(s, 160)}"')

    # # 返回prod_reward最大的response
    # 返回last_reward最大的response
    final_result = ''
    max_reward = 0
    final_id = -1
    # for i in range(n):
    #     if res_dict[i]["prod_reward"] > max_reward:
    #         max_reward = res_dict[i]["prod_reward"]
    #         final_id = i
    for i in range(n):
        if res_dict[i]["last_reward"] > max_reward:
            max_reward = res_dict[i]["last_reward"]
            final_id = i

    final_result = res_dict[final_id]['response']
    final_result_tail = {' '.join(final_result.split('\n'))}
    dgreen(f'final answer: "{final_result_tail}"')
    return final_result


def console_asks(prompt, temperature, max_new_tokens=8192):
    # 安装curses
    # windows: pip install windows-curses
    # linux: pip install curses
    import curses
    curses.wrapper(_console_asks, prompt=prompt, temperature=temperature, max_new_tokens=max_new_tokens)


def hot_temp_main():
    llm = LLM_Client(
        api_key='empty',
        url='http://localhost:8022/v1',
        max_new_tokens=8192,
    )
    llm.ask_prepare('1+1=', temperature=0.5, max_new_tokens=1).get_answer_and_sync_print()
    llm.ask_prepare('继续', temperature=0.5, max_new_tokens=100).get_answer_and_sync_print()


def o1_BoN_all(question, temperature=1.0, n=64):
    # # prompt='''51.2亿kWh是多少kWh？'''
    # prompt='''一元钱可以买一瓶可乐，且喝了可乐后，两个空瓶可以免费换一瓶新的可乐，请问15元一共可以喝几瓶可乐？'''
    # console_asks(prompt=prompt, temperature=0.7)
    # # console_asks(prompt='51.2亿kWh是多少kWh？', temperature=1.0)
    # # hot_temp_main()

    from config import get_os

    # prompt='''51.2亿kWh是多少kWh？'''
    # prompt='''一元钱可以买一瓶可乐，且喝了可乐后，两个空瓶可以免费换一瓶新的可乐，请问22元一共可以喝几瓶可乐？'''
    if get_os() == 'windows':
        final_answer = ask_with_prm(
            llm_url='http://localhost:8001/v1',
            prm_model_path='d:/models/Skywork-o1-Open-PRM-Qwen-2.5-7B',
            question=question,
            temperature=temperature,
            n=n
        )
    else:
        final_answer = ask_with_prm(
            question=question,
            temperature=temperature,
            n=n
        )
    print(f'final_answer:')
    print(final_answer)
    return final_answer


def o1_steps_search(question, messages, llm_key='empty', prm_key='empty', llm_url='https://powerai.cc:8001/v1',
                    prm_url='https://powerai.cc:8002/v1',
                    max_new_tokens=1024, temperature=0.7, n=10,
                    prm_model_path='/home/tutu/models/Skywork-o1-Open-PRM-Qwen-2.5-7B'):
    from tools.llm.api_prm_client import LLM_PRM_Client, Step_Data

    # 给prm的response是['assistant step response...', ...].append(res)，然后'\n'.join()
    his_responses_list = []
    for dict in messages:
        if 'role' in dict and dict['role'] == 'assistant':
            his_responses_list.append(dict['content'])

    dgreen(f'history responses:')
    dgreen('\n'.join(his_responses_list))

    def message_stream(gen):
        for chunk in gen:
            if chunk.choices and hasattr(chunk.choices[0].delta, "content") and chunk.choices[
                0].delta.content is not None:
                yield chunk.choices[0].delta.content

    res_dict = {}

    oai = OpenAI(
        api_key=llm_key,
        base_url=llm_url,
    )
    model_id = oai.models.list().data[0].id
    messages1 = [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user',
         'content': '''一元钱可以买一瓶可乐，且喝了可乐后，两个空瓶可以免费换一瓶新的可乐，请问22元一共可以喝几瓶可乐？'''},
        {'role': 'assistant', 'content': '为了解决这个问题，我们可以分步骤来计算。'},
        {'role': 'assistant', 'content': '首先，直接用22元购买可乐，不考虑回收空瓶换购的情况。'},
        {'role': 'assistant', 'content': '1. **直接购买的可乐数量**：22元直接可以买22瓶可乐。'},
        {'role': 'assistant',
         'content': '2. **喝完第一轮的可乐后，收集空瓶换购**：喝完22瓶可乐，会得到22个空瓶，用其中的20个空瓶可以换购10瓶新的可乐（因为每2个空瓶可以换1瓶新的可乐）。'},
        {'role': 'assistant',
         'content': '3. **喝完换购来的可乐后，收集空瓶再次换购**：喝完这10瓶可乐，又会得到10个空瓶，用其中的8个空瓶可以换4瓶新的可乐。'},
        {'role': 'assistant',
         'content': '4. **重复上述过程**：喝完这4瓶可乐，得到4个空瓶，用其中的4个空瓶再换2瓶新的可乐。接着，喝完这2瓶可乐，得到2个空瓶，用这2个空瓶换1瓶新的可乐。最后，喝完这瓶可乐，再没有足够的空瓶去换新的可乐了。'},
        {'role': 'assistant',
         'content': '将所有喝到的可乐数量加起来：22（初始购买）+ 10（第一次换购）+ 4（第二次换购）+ 2（第三次换购）+ 1（第四次换购）= 39瓶。'},
        {'role': 'assistant', 'content': '因此，22元一共可以喝到39瓶可乐。'},
        {'role': 'assistant', 'content': '等一下，'},
    ]

    def _task(id):
        prm = LLM_PRM_Client()
        prm.init(prm_model_path=prm_model_path, url=prm_url, api_key=prm_key)

        stop = ['\n']
        gen = oai.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=temperature,
            stream=True,
            max_tokens=max_new_tokens,
            stop=stop,
        )

        res = ''
        for chunk in message_stream(gen):
            res += chunk

        # 给prm的response是['assistant step response...', ...].append(res)，然后'\n'.join()
        his_res = '\n'.join(his_responses_list) + '\n' + res
        # dgreen(f'history responses:')
        # dgreen(f'{res}')

        # 获取step_rewards
        step_data = Step_Data(problem=question, response=his_res)
        step_rewards = prm.get_step_rewards(step_data)

        res_dict[id] = {
            'response': res,
            'step_rewards': step_rewards,
            'min_reward': prm.get_min_reward(),
            'last_reward': prm.get_last_reward(),
            'prod_reward': prm.get_prod_reward(),
        }

    # 启动callback任务
    threads = []
    for i in range(n):  # 有10个线程
        t = threading.Thread(target=_task, args=(i,))
        threads.append(t)
        t.start()

    # 等待所有任务完成
    for t in threads:
        t.join()

    from utils.string_util import string_right_align
    for i in range(n):
        s = ' '.join(res_dict[i]['response'][-50:].split('\n'))
        rewards_list = [f'{r:.2f}' for r in res_dict[i]['step_rewards']]
        # s += f'【{",".join(rewards_list)}】'
        s += f'【min: {res_dict[i]["min_reward"]:.2f}】'
        s += f'【prod: {res_dict[i]["prod_reward"]:.9f}】'
        s += f'【last: {res_dict[i]["last_reward"]:.2f}】'
        print(f'[{i}]: "...{string_right_align(s, 180)}"')

    # # 返回prod_reward最大的response
    # 返回last_reward最大的response
    final_result = ''
    max_reward = 0
    final_id = -1
    # for i in range(n):
    #     if res_dict[i]["prod_reward"] > max_reward:
    #         max_reward = res_dict[i]["prod_reward"]
    #         final_id = i
    for i in range(n):
        if res_dict[i]["last_reward"] > max_reward:
            max_reward = res_dict[i]["last_reward"]
            final_id = i

    final_result = res_dict[final_id]['response']
    dred(f'final answer: ')
    dred(f'"{final_result}"')

    return final_result


def o1_BoN_steps(question, temperature=0.7, n=16, max_tries=10):
    messages = [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': question},

    ]
    res = o1_steps_search(question=question, messages=messages, temperature=temperature, n=n)

    for i in range(max_tries):
        messages.append({'role': 'assistant', 'content': res})
        res = o1_steps_search(question=question, messages=messages, temperature=temperature, n=n)

    print(f'final_result: {res}')
    return res


g_prompt = '''你正在编制一份可行性研究报告，请严格按照【输入资料】、【用户要求】和【输出文本要求】，对报告内容进行编制：

######输入资料######
表2.8.2-1			2024年短路电流计算结果表				单位：kA
节点	三相	单相
洛迦变500kV母线	28.0	40.9
洛迦变220kV母线	57.8/46.6	34.1/35.5
蓬莱变220kV母线	36.1	20.5
蓬莱变110kV母线	41.1	9.2
沈家湾变110kV母线	16.1	7.9
洋山光伏110kV母线	5.3	6.4

表2.8.2-2			2035年短路电流计算结果表				单位：kA
节点	三相	单相
洛迦变500kV母线	26.3	38.9
洛迦变220kV母线	45.7/43.8	32.0/33.1
蓬莱变220kV母线	53.3	18.2
蓬莱变110kV母线	10.0	9.1
沈家湾变110kV母线	5.9	7.7
洋山光伏110kV母线	45.1	6.2

######用户要求######
请检查【输入资料】的表格中是否存在厂站其500kV、220kV或110kV母线短路电流超限（500kV母线额定短路电流为63kA，220kV母线额定短路电流为50kA，110kV母线额定短路电流为40kA）的情况，将所有存在超限的情况编写到【输出文本】中。

######输出文本要求（不要任何额外的解释，必须直接输出）######
a）先输出一步一步的分析，所有分析用一个<thinking></thinking>包裹。
b）如果各厂站母线的短路电流均未超标，编写输出如下：
{‘table‘: 这里放输入资料的完整内容, ‘report’:’报告对短路电流进行了计算，短路电流计算表明，各相关厂站短路电流均得到合理的控制，各500kV厂站短路电流均控制在63kA以内，220kV母线短路电流控制在50kA以内，110kV母线短路电流控制在40kA以内。’}
c）如有厂站母线的短路电流超标，编写输出如下（绝对不能遗漏短路电流超标的厂站）：
{‘table‘:这里放输入资料的完整内容, ‘report’:’报告对短路电流进行了计算，短路电流计算表明，xxx 500kV xx站220kV短路电流（xx kA）超限，xxx 220kV xx站220kV母线短路电流（xx kA）超限，xxx 110kV xx站110kV母线短路电流（xx kA）超限，…。其余厂站短路电流均得到了合理的控制。’}
'''


def think_main():
    llm = LLM_Client(
        temperature=0.7,
        url='https://powerai.cc:8001/v1'
    )

    # llm.ask_prepare('1+1=？',
    #                 temperature=0,
    #                 max_new_tokens=500,
    #                 # remove_content_in_think_pairs=False,
    #                 remove_content_in_think_pairs=True,
    #                 think_pair=('<think>', '</think>'),
    #                 ).get_answer_and_sync_print()
    gen = llm.ask_prepare(
        '你是谁？',
        # remove_content_in_think_pairs=True,
        # think_pair=('<think>', '</think>')
    ).get_answer_generator()

    for chunk in gen:
        print(chunk)
    # print(f'\n--------answer_last_turn--------\n{llm.answer_last_turn}')
    print(f'--------------------------------')


def base_main():
    llm = LLM_Client(
        # llm_config=config.g_local_gpt_oss_20b_mxfp4,
        llm_config=config.g_local_qwen3_30b_chat,
        # llm_config=config.g_local_qwen3_30b_thinking,
    )
    # llm.ask_prepare('1+1=?只给出答案').get_answer_and_sync_print()
    llm.ask_prepare('你是谁？我叫土土，你好。').get_answer_and_sync_print()
    # llm.ask_prepare('我叫土土').get_answer_and_sync_print()
    llm.ask_prepare('我刚才告诉你我叫什么？').get_answer_and_sync_print()
    # llm.ask_prepare('2+3=').get_answer_and_sync_print()

def reasoning_effort_main():
    llm = LLM_Client(
        llm_config=config.g_local_gpt_oss_20b_mxfp4,
    )
    prompt = '桌子上有16张扑克牌:红桃2、6，黑桃2、5、K，草花3、5、8、9、Q，方块A、5、6、7、K。从这16张牌中拱出一张牌并把这张牌的点数告诉x先生，把这张牌的花色告诉Y先生。这时，问x先生和Y先生:你们能从已知的点数或花色中推知这张牌是什么牌吗?x先生:我不知道这张牌。Y先生:我知道你不知道这张牌。x先生:现在我知道这张牌了。丫先生:我也知道了。问，这张牌是多少?'
    llm.ask_prepare(prompt).get_answer_and_sync_print()

def think_and_result_test():
    llm = LLM_Client(
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',  # deepseek官网
        url='https://api.deepseek.com/v1',
        model_id='deepseek-reasoner',  # 模型指向 DeepSeek-R1-0528
        # model_id='deepseek-chat',  # 模型指向 DeepSeek-V3-0324
    )
    llm.ask_prepare('你是谁？')
    think_gen = llm.get_think_generator()
    dyellow('[thinking]')
    for c in think_gen:
        print(c, end='', flush=True)
    dyellow('\n[/thinking]')

    dgreen('[result]')
    result_gen = llm.get_result_generator()
    for c in result_gen:
        print(c, end='', flush=True)
    dgreen('\n[/result]')


def async_llm_main():
    allm = Async_LLM(
        question='你是谁',
        url='https://api.deepseek.com/v1',
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        temperature=0.6,
    )
    allm.init()
    allm.set_stream_result(dyellow)
    allm.start()
    print('quit.')
    allm.wait()


def llm_config_test():
    from config import g_online_deepseek_chat, g_online_groq_kimi_k2

    llm = LLM_Client(llm_config=g_online_groq_kimi_k2)
    # llm = LLM_Client(llm_config=g_online_deepseek_chat)

    llm.ask_prepare('你是谁？').get_answer_and_sync_print()

if __name__ == "__main__":
    # base_main()

    reasoning_effort_main()

    # llm_config_test()

    # pic_main() # 带pic
    # think_and_result_test()
    # async_llm_main()

    # think_main()

    # 直接采样64个完整结果的BoN筛选的正确率，比每个step采样20次、最多尝试10个steps的BoN筛选的正确率高，且step方式采用不清楚多少steps刚好完成。
    # question = '一元钱可以买一瓶可乐，且喝了可乐后，两个空瓶可以免费换一瓶新的可乐，请问22元一共可以喝几瓶可乐？'
    # question = g_prompt
    # o1_BoN_all(question=question, temperature=0.7, n=32)
    # o1_BoN_steps(question=question, temperature=0.7, n=20, max_tries=10)