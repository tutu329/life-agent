from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Union, Tuple, TYPE_CHECKING
from config import dred,dyellow,dblue,dcyan,dgreen

@dataclass
class Config:
    is_web_server:              bool = False    # agent是否为web-server
    stream_result:              Any = None      # agent最终答复result的stream输出func, 如print或streamlit的st.some_component.empty().markdown
    stream_thinking:            Any = None      # agent思考过程thinking的stream输出func
    stream_log:                 Any = None      # agent日志信息log的stream输出func
    stream_tool_client_data:    Any = None      # agent工具调用结果数据的stream输出func
