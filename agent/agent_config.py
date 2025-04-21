from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Union, Tuple, TYPE_CHECKING
from config import dred,dyellow,dblue,dcyan,dgreen

import config

@dataclass
class Config:
    # 基本配置
    output_end:Any = None                   # 最终答复输出end的func
    output_stream_to_console:bool = False    # 最终答复是否stream输出到console
    output_stream_use_chunk:bool = True      # 最终答复stream输出是否采用chunk方式，还是full_string方式
    inout_output_list:Any = None
    status_stream_buf:Any = None

    base_url:str = config.LLM_Default.url
    api_key:str = 'empty'
    model_id:str = ''
    temperature:float = config.LLM_Default.temperature

    # web-server相关配置
    is_web_server:              bool = False    # agent是否为web-server
    stream_result:              Any = None      # agent最终答复result的stream输出func, 如print或streamlit的st.some_component.empty().markdown
    stream_thinking:            Any = None      # agent思考过程thinking的stream输出func
    stream_log:                 Any = None      # agent日志信息log的stream输出func
    stream_tool_client_data:    Any = None      # agent工具调用结果数据的stream输出func
