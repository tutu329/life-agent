import os
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union, Tuple, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict

class Port:
    # frp的port范围
    # 5100-5120
    # 7860-7879
    # 8012-8020
    # 8001-8011

    comfy                               :int = 5100     # ComfyUI

    # 前端项目life_agent_web相关
    agent_web                           :int = 5101
    agent_web_only_office_server        :int = 5102     # only-office-server

    # 后端agent用的tool相关
    agent_fastapi_server                :int = 5110     # 后端agent的server
    remote_tool_fastapi_server          :int = 5111     # 后端agent的remote_tools
    collabora_code_web_socket_server    :int = 5112     # 前端collabora CODE office控件(基于libre-office，完全开源、可商用)被后台agent控制的端口

    # 顶层应用
    flowise:int         = 7860
    llm_ui: int         = 7861

    # 工作环境
    jupyter:int         = 7862
    fastgpt: int        = 7863
    open_webui:int      = 7864 # open-webui
    jupyter_temp:int    = 7865 # 自定义jupyter的docker容器

    dify: int           = 7866
    sovit: int          = 7867
    llm_viz:int         = 7869  # 三维演示gpt结构

    openwebui: int      = 7870
    m3e_api:int         = 7870 # 由xinference发布的

    ragflow: int        = 7871

    # api底层服务
    qdrant1:int         = 7872 # qdrant
    qdrant2:int         = 7873 # qdrant

    llm_api0:int        = 8000 # vllm
    llm_api1:int        = 8001 # vllm
    llm_api2:int        = 8002 # vllm

    # api转发层
    one_api:int         = 8002 # flowise等顶层应用可以直接调用:8002/v1的llm_api和m3e_api

    milvus_api:int      = 8003 # milvus单独的api
    chroma_api:int      = 8004 # chroma单独的api

    redis_monitor:int   = 8009 # redis monitor
    redis_client:int    = 8010 # redis消息服务

    # sd:int              = 7868  # stable diffusion
    # comfy:int           = 7869  # ComfyUI

class LLM_Default:
    server_domain:str = 'powerai.cc'

    temperature:float   = 0.6
    top_p:float         = 0.95
    max_new_tokens:int  = 8192
    # stop:List[str]      = field(default_factory=list)
    stream:int         = 1          # 注意这里不能用bool，因为经过redis后，False会转为‘0’, 而字符‘0’为bool的True
    history:int        = 1          # 注意这里不能用bool，因为经过redis后，False会转为‘0’, 而字符‘0’为bool的True
    clear_history:int  = 0          # 用于清空history_list, 注意这里不能用bool，因为经过redis后，False会转为‘0’, 而字符‘0’为bool的True
    api_key:str         = 'empty'

    url:str             = f'https://{server_domain}:{Port.llm_api1}/v1'

    think_pairs: tuple  = ('<think>', '</think>')

class Reasoning_Effort(str, Enum):
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

    reasoning_effort:Optional[Reasoning_Effort] = None

    vpn_on          :bool = False

g_vpn_proxy = "http://127.0.0.1:7890"

g_local_gpt_oss_20b_mxfp4 = LLM_Config(
    base_url='http://powerai.cc:18002/v1',
    api_key='empty',
    # llm_model_id='',
    temperature=0.6,
    top_p=0.8,
    max_new_tokens=8192,
    # reasoning_effort=Reasoning_Effort.HIGH
    reasoning_effort=Reasoning_Effort.LOW
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