import os
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union, Tuple, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict
from uuid import uuid4

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
    clear_history:int   = 0             # 用于ask_prepare()中的清空history_list, 注意这里不能用bool，因为经过redis后，False会转为‘0’, 而字符‘0’为bool的True
    api_key:str         = 'empty'

    system_prompt:str   ='You are a helpful assistant.'
    role_prompt:str     =''

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
    stream          :bool = bool(LLM_Default.stream)
    manual_stop     :Optional[List[str]] = None  # 用于vllm处理stop有bug

    system_prompt   :str = LLM_Default.system_prompt
    role_prompt     :str = LLM_Default.role_prompt

    # llm推理强度(用于支持GPT-oss的推理强度选择)
    reasoning_effort:Optional[LLM_Reasoning_Effort] = None
    use_harmony     :bool = False   # openai主推的对话/工具调用格式（增强agent能力，且目前vllm的completion接口有bug，必须用harmony格式；GPT-oss模型是在harmony格式上训练的。）

    # llm是否通过vpn访问
    vpn_on          :bool = False

    # response接口还是chatml接口
    chatml          :bool = False   # False表示为response接口

    # llm在对话层面的参数
    has_history         :bool = bool(LLM_Default.has_history)
    history_max_turns   :int = LLM_Default.history_max_turns
    history_clear_method:LLM_Clear_History_Method = LLM_Clear_History_Method.POP

    def __str__(self):
        data = self.model_dump()
        rtn_str = f'llm config "{self.name}"'.center(80, '-') + '\n'
        rtn_str += '\n'.join(f'{k:21}: {v!r}' for k, v in data.items()) + '\n'
        rtn_str += f'/llm config "{self.name}"'.center(80, '-')
        return rtn_str

class LLM_Query_Paras(BaseModel):
    # query的id(session id)
    id              :str = Field(default_factory=lambda:str(uuid4()))

    # query相关参数
    query           :str
    image_url      :Optional[str] = None
    clear_history   :bool = bool(LLM_Default.clear_history)

    # 这些config相关参数，若为None，则将在LLM_Client.ask_prepare()中被self.llm_config中参数覆盖
    temperature     :Optional[float] = None
    top_p           :Optional[float] = None
    max_new_tokens  :Optional[int] = None
    system_prompt   :Optional[str] = None
    role_prompt     :Optional[str] = None
    manual_stop     :Optional[List[str]] = None  # 用于vllm处理stop有bug

    def __str__(self):
        data = self.model_dump()
        rtn_str = f'llm query "{self.id}"'.center(80, '-') + '\n'
        rtn_str += '\n'.join(f'{k:16}: {v!r}' for k, v in data.items()) + '\n'
        rtn_str += f'/llm query "{self.id}"'.center(80, '-')
        return rtn_str

g_local_gpt_oss_20b_mxfp4 = LLM_Config(
    name = 'local_gpt_oss_20b_mxfp4',
    base_url='http://powerai.cc:18002/v1',
    api_key='empty',
    llm_model_id='gpt-oss-20b-mxfp4',
    temperature=1.0,
    top_p=1.0,
    max_new_tokens=8192,
    # reasoning_effort=LLM_Reasoning_Effort.HIGH,
    # reasoning_effort=LLM_Reasoning_Effort.MEDIUM,
    reasoning_effort=LLM_Reasoning_Effort.LOW,
    chatml=False,
)

g_local_gpt_oss_20b_mxfp4_lmstudio = LLM_Config(
    name = 'local_gpt_oss_20b_mxfp4_lmstudio',
    base_url='http://powerai.cc:8001/v1',
    api_key='empty',
    llm_model_id='openai/gpt-oss-20b',
    temperature=1.0,
    top_p=1.0,
    # temperature=0.6,
    # top_p=0.95,
    max_new_tokens=8192,
    reasoning_effort=LLM_Reasoning_Effort.HIGH,
    # reasoning_effort=LLM_Reasoning_Effort.MEDIUM,
    # reasoning_effort=LLM_Reasoning_Effort.LOW,
    chatml=True,
)

g_local_gpt_oss_120b_mxfp4_lmstudio = LLM_Config(
    name = 'local_gpt_oss_120b_mxfp4_lmstudio',
    base_url='http://powerai.cc:8001/v1',
    api_key='empty',
    llm_model_id='openai/gpt-oss-120b',
    temperature=1.0,
    top_p=1.0,
    # temperature=0.6,
    # top_p=0.95,
    max_new_tokens=8192,
    reasoning_effort=LLM_Reasoning_Effort.HIGH,
    # reasoning_effort=LLM_Reasoning_Effort.MEDIUM,
    # reasoning_effort=LLM_Reasoning_Effort.LOW,
    chatml=True,
)

g_local_qwen3_30b_chat = LLM_Config(
    name = 'local_qwen3_30b_chat',
    base_url='https://powerai.cc:8001/v1',
    api_key='empty',
    llm_model_id='Qwen3-30B-A3B-Instruct-2507',
    temperature=0.7,
    top_p=0.8,
    chatml=True,
    max_new_tokens=8192
)

g_local_qwen3_30b_thinking = LLM_Config(
    name = 'local_qwen3_30b_thinking',
    base_url='https://powerai.cc:8001/v1',
    api_key='empty',
    llm_model_id='Qwen3-30B-A3B-Thinking-2507',
    temperature=0.6,
    top_p=0.95,
    chatml=True,
    max_new_tokens=8192
)

g_local_qwen3_4b_thinking = LLM_Config(
    name = 'local_qwen3_4b_thinking',
    base_url='https://powerai.cc:8001/v1',
    api_key='empty',
    # llm_model_id='',
    temperature=0.6,
    top_p=0.95,
    chatml=True,
    max_new_tokens=8192
)

g_online_deepseek_chat = LLM_Config(
    name = 'online_deepseek_chat',
    base_url='https://api.deepseek.com/v1',
    api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
    llm_model_id='deepseek-chat',
    temperature=0.6,
    top_p=0.95,
    chatml=True,
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
    chatml=True,
    vpn_on=True
)

g_online_groq_gpt_oss_20b = LLM_Config(
    name = 'online_groq_gpt_oss_20b',
    base_url='https://api.groq.com/openai/v1',
    api_key=os.getenv("GROQ_API_KEY") or 'empty',
    llm_model_id='openai/gpt-oss-20b',
    temperature=1.0,
    # temperature=0.6,
    top_p=1.0,
    # top_p=0.95,
    max_new_tokens=8192,
    reasoning_effort=LLM_Reasoning_Effort.LOW, # groq似乎不支持reasoning_effort
    # reasoning_effort=LLM_Reasoning_Effort.MEDIUM, # groq似乎不支持reasoning_effort
    # reasoning_effort=LLM_Reasoning_Effort.HIGH, # groq似乎不支持reasoning_effort
    use_harmony=True,
    chatml=False,
    vpn_on=True
)

g_online_groq_gpt_oss_120b = LLM_Config(
    name = 'online_groq_gpt_oss_120b',
    base_url='https://api.groq.com/openai/v1',
    api_key=os.getenv("GROQ_API_KEY") or 'empty',
    llm_model_id='openai/gpt-oss-120b',
    temperature=1.0,
    # temperature=0.6,
    top_p=1.0,
    # top_p=0.95,
    max_new_tokens=8192,
    # reasoning_effort=LLM_Reasoning_Effort.HIGH, # groq似乎不支持reasoning_effort
    reasoning_effort=LLM_Reasoning_Effort.LOW, # groq似乎不支持reasoning_effort
    use_harmony=True,
    chatml=False,
    vpn_on=True
)
