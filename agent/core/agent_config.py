from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Union, Tuple, TYPE_CHECKING
from config import dred,dyellow,dblue,dcyan,dgreen
from pydantic import BaseModel, Field, ConfigDict

import config

# @dataclass
# class Agent_Config:
#     # 基本配置
#     output_end:Any = None                   # 最终答复输出end的func
#     output_stream_to_console:bool = True    # 最终答复是否stream输出到console
#     output_stream_use_chunk:bool = True     # 最终答复stream输出是否采用chunk方式，还是full_string方式
#     inout_output_list:Any = None
#     status_stream_buf:Any = None
#
#     base_url:str = config.LLM_Default.url
#     api_key:str = 'empty'
#     llm_model_id:str = ''
#     temperature:float = config.LLM_Default.temperature
#
#     # web-server相关配置
#     is_web_server:              bool = False    # agent是否为web-server
#     web_server_stream_result:              Any = None      # agent最终答复result的stream输出func, 如print或streamlit的st.some_component.empty().markdown
#     web_server_stream_thinking:            Any = None      # agent思考过程thinking的stream输出func
#     web_server_stream_log:                 Any = None      # agent日志信息log的stream输出func
#     web_server_stream_tool_client_data:    Any = None      # agent工具调用结果数据的stream输出func

class Agent_Config(BaseModel):
    # 基本配置
    # output_end:Any = None                   # 最终答复输出end的func
    # output_stream_to_console:bool = True    # 最终答复是否stream输出到console
    # output_stream_use_chunk:bool = True     # 最终答复stream输出是否采用chunk方式，还是full_string方式
    # inout_output_list:Any = None
    # status_stream_buf:Any = None

    base_url:str = config.LLM_Default.url
    api_key:str = 'empty'
    llm_model_id:str = ''
    temperature:float = config.LLM_Default.temperature

    # web-server相关配置
    # is_web_server:              bool = False    # agent是否为web-server
    # web_server_stream_result:              Any = None      # agent最终答复result的stream输出func, 如print或streamlit的st.some_component.empty().markdown
    # web_server_stream_thinking:            Any = None      # agent思考过程thinking的stream输出func
    # web_server_stream_log:                 Any = None      # agent日志信息log的stream输出func
    # web_server_stream_tool_client_data:    Any = None      # agent工具调用结果数据的stream输出func
