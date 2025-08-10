import os
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union, Tuple, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict

import config

class LLM_Default:
    temperature:float   = 0.6
    top_p:float         = 0.95
    max_new_tokens:int  = 8192
    # stop:List[str]      = field(default_factory=list)
    stream:int         = 1          # 注意这里不能用bool，因为经过redis后，False会转为‘0’, 而字符‘0’为bool的True
    history:int        = 1          # 注意这里不能用bool，因为经过redis后，False会转为‘0’, 而字符‘0’为bool的True
    clear_history:int  = 0          # 用于清空history_list, 注意这里不能用bool，因为经过redis后，False会转为‘0’, 而字符‘0’为bool的True
    api_key:str         = 'empty'

    url:str             = f'https://{config.Domain.server_domain}:{config.Port.llm_api1}/v1'

    think_pairs: tuple  = ('<think>', '</think>')

class LLM_Reasoning_Effort(str, Enum):
    LOW     = 'low'
    MEDIUM  = 'medium'
    HIGH    = 'high'

class LLM_Config(BaseModel):
    base_url        :str = LLM_Default.url
    api_key         :str = 'empty'
    llm_model_id    :str = ''
    temperature     :float = LLM_Default.temperature
    top_p           :float = LLM_Default.top_p
    max_new_tokens  :int = LLM_Default.max_new_tokens

    reasoning_effort:Optional[LLM_Reasoning_Effort] = None

    vpn_on          :bool = False

g_local_gpt_oss_20b_mxfp4 = LLM_Config(
    base_url='http://powerai.cc:18002/v1',
    api_key='empty',
    # llm_model_id='',
    temperature=0.6,
    top_p=0.8,
    max_new_tokens=8192,
    # reasoning_effort=Reasoning_Effort.HIGH
    reasoning_effort=LLM_Reasoning_Effort.LOW
)

g_local_qwen3_30b_chat = LLM_Config(
    base_url='https://powerai.cc:8001/v1',
    api_key='empty',
    # llm_model_id='',
    temperature=0.7,
    top_p=0.8,
    max_new_tokens=8192
)

g_local_qwen3_30b_thinking = LLM_Config(
    base_url='https://powerai.cc:8002/v1',
    api_key='empty',
    # llm_model_id='',
    temperature=0.6,
    top_p=0.95,
    max_new_tokens=8192
)

g_online_deepseek_chat = LLM_Config(
    base_url='https://api.deepseek.com/v1',
    api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
    llm_model_id='deepseek-chat',
    temperature=0.6,
    top_p=0.95,
    max_new_tokens=8192
)

g_online_groq_kimi_k2 = LLM_Config(
    base_url='https://api.groq.com/openai/v1',
    api_key=os.getenv("GROQ_API_KEY") or 'empty',
    llm_model_id='moonshotai/kimi-k2-instruct',
    temperature=0.6,
    top_p=0.95,
    max_new_tokens=8192,
    vpn_on=True
)