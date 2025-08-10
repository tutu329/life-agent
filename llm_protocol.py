import os
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union, Tuple, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict

import config
from config import dred, dyellow, dblue, dcyan

class LLM_Default:
    temperature:float   = 0.6
    top_p:float         = 0.95
    max_new_tokens:int  = 8192
    # stop:List[str]      = field(default_factory=list)
    stream:int              = 1         # 注意这里不能用bool，因为经过redis后，False会转为‘0’, 而字符‘0’为bool的True
    has_history:int         = 1         # 注意这里不能用bool，因为经过redis后，False会转为‘0’, 而字符‘0’为bool的True
    history_max_turns:int   = 99999     # 注意这里不能用bool，因为经过redis后，False会转为‘0’, 而字符‘0’为bool的True
    clear_history:int   = 0          # 用于清空history_list, 注意这里不能用bool，因为经过redis后，False会转为‘0’, 而字符‘0’为bool的True
    api_key:str         = 'empty'

    url:str             = f'https://{config.Domain.server_domain}:{config.Port.llm_api1}/v1'

    think_pairs: tuple  = ('<think>', '</think>')

class LLM_Reasoning_Effort(str, Enum):
    LOW     = 'low'
    MEDIUM  = 'medium'
    HIGH    = 'high'

class LLM_Clear_History_Method(str, Enum):
    CLEAR     = 'clear'
    POP     = 'pop'

class LLM_Config(BaseModel):
    # 配置名称
    name            :str = 'default llm config 1'

    # llm基本参数
    base_url        :str = LLM_Default.url
    api_key         :str = 'empty'
    llm_model_id    :str = ''
    temperature     :float = LLM_Default.temperature
    top_p           :float = LLM_Default.top_p
    max_new_tokens  :int = LLM_Default.max_new_tokens

    # llm推理强度(用于支持GPT-oss的推理强度选择)
    reasoning_effort:Optional[LLM_Reasoning_Effort] = None

    # llm是否通过vpn访问
    vpn_on          :bool = False

    # llm在对话层面的参数
    has_history         :bool = bool(LLM_Default.has_history)
    history_max_turns   :int = LLM_Default.history_max_turns
    history_clear_method:LLM_Clear_History_Method = LLM_Clear_History_Method.POP

    def __str__(self):
        data = self.model_dump()
        rtn_str = f'"{self.name}"'.center(80, '-') + '\n'
        rtn_str += '\n'.join(f'{k:21}: {v!r}' for k, v in data.items()) + '\n'
        rtn_str += f'/"{self.name}"'.center(80, '-')
        return rtn_str

g_local_gpt_oss_20b_mxfp4 = LLM_Config(
    name = 'local_gpt_oss_20b_mxfp4',
    base_url='http://powerai.cc:18002/v1',
    api_key='empty',
    # llm_model_id='',
    temperature=0.6,
    top_p=0.95,
    max_new_tokens=8192,
    # reasoning_effort=Reasoning_Effort.HIGH
    reasoning_effort=LLM_Reasoning_Effort.LOW
)

g_local_qwen3_30b_chat = LLM_Config(
    name = 'local_qwen3_30b_chat',
    base_url='https://powerai.cc:8001/v1',
    api_key='empty',
    # llm_model_id='',
    temperature=0.7,
    top_p=0.8,
    max_new_tokens=8192
)

g_local_qwen3_30b_thinking = LLM_Config(
    name = 'local_qwen3_30b_thinking',
    base_url='https://powerai.cc:8002/v1',
    api_key='empty',
    # llm_model_id='',
    temperature=0.6,
    top_p=0.95,
    max_new_tokens=8192
)

g_online_deepseek_chat = LLM_Config(
    name = 'online_deepseek_chat',
    base_url='https://api.deepseek.com/v1',
    api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
    llm_model_id='deepseek-chat',
    temperature=0.6,
    top_p=0.95,
    max_new_tokens=8192
)

g_online_groq_kimi_k2 = LLM_Config(
    name = 'online_groq_kimi_k2',
    base_url='https://api.groq.com/openai/v1',
    api_key=os.getenv("GROQ_API_KEY") or 'empty',
    llm_model_id='moonshotai/kimi-k2-instruct',
    temperature=0.6,
    top_p=0.95,
    max_new_tokens=8192,
    vpn_on=True
)