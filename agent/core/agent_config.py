from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Union, Tuple, TYPE_CHECKING
from config import dred,dyellow,dblue,dcyan,dgreen
from pydantic import BaseModel, Field, ConfigDict

import config
import llm_protocol
from llm_protocol import LLM_Config
from agent.tools.protocol import Tool_Request
from agent.core.mcp.protocol import MCP_Server_Request

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

    # agent配置
    agent_name          :Optional[str] = None           # agent的name
    exp_json_path       :str = ''                       # 如：'my_2_levels_mas_exp.json'
    agent_max_retry         :int = config.Agent.MAX_RETRY       # agent循环的最大次数
    agent_max_error_retry   :int = config.Agent.MAX_ERROR_RETRY # agent循环中遇到错误后的最大尝试次数

    # 普通tools
    allowed_local_tool_names          :Optional[List[str]] = None     # 如：['Human_Console_Tool', 'Remote_Folder_Tool']
    tool_names          :Optional[List[str]] = None           # 如：['Human_Console_Tool', 'Remote_Folder_Tool']
    tool_objects        :Optional[List[Tool_Request]] = None

    # MCP tools
    mcp_requests :Optional[List[MCP_Server_Request]] = None                # 如: [("https://powerai.cc:8011/mcp/sqlite/sse",['read_query', 'write_query']), ("http://localhost:8789/sse", [...])]

    # LLM配置
    llm_config          :LLM_Config = llm_protocol.g_local_gpt_oss_120b_mxfp4_lmstudio

    has_history         :bool = False
    tool_agent_experience_json_path     :str = ''  # 经验json文件，如果为‘’，就不设置经验
    top_agent_id        :Optional[str] = None  # top_agent_id为None时，表明自己即为top agent

    # agent_as_tool配置
    as_tool_name        :Optional[str] = None  # As_Tool的name，如取: "Folder_Agent_As_Tool"
    as_tool_description :Optional[str] = None  # As_Tool的description，如取: "本工具用来获取某个文件夹下的信息"

    # base_url        :str = config.LLM_Default.url


    # web-server相关配置
    # is_web_server:              bool = False    # agent是否为web-server
    # web_server_stream_result:              Any = None      # agent最终答复result的stream输出func, 如print或streamlit的st.some_component.empty().markdown
    # web_server_stream_thinking:            Any = None      # agent思考过程thinking的stream输出func
    # web_server_stream_log:                 Any = None      # agent日志信息log的stream输出func
    # web_server_stream_tool_client_data:    Any = None      # agent工具调用结果数据的stream输出func

    def __str__(self):
        data = self.model_dump()
        rtn_str = f'agent config "{self.agent_name}"'.center(80, '-') + '\n'
        rtn_str += '\n'.join(f'{k:21}: {v!r}' for k, v in data.items()) + '\n'
        rtn_str += f'/agent config "{self.agent_name}"'.center(80, '-')
        return rtn_str

class Agent_As_Tool_Config(BaseModel):
    # agent配置
    tool_names              :List[str]  # 如：['Human_Console_Tool', 'Remote_Folder_Tool']
    exp_json_path           :str = ''   # 如：'my_2_levels_mas_exp.json'
    as_tool_name            :str        # 如：'Folder_Agent_As_Tool'
    as_tool_description     :str        # 如：'本工具用于获取文件夹中的文件和文件夹信息'

    llm_config              :LLM_Config = llm_protocol.g_online_groq_kimi_k2

    # LLM配置
    # base_url        :str = config.LLM_Default.url
    # api_key         :str = 'empty'
    # llm_model_id    :str = ''
    # temperature     :float = config.LLM_Default.temperature

    # 开启“任意类型”支持
    # model_config = ConfigDict(arbitrary_types_allowed=True)
