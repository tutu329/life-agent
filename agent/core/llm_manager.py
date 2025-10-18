from typing import Any, Dict, List, Set, Literal, Optional, Union, Tuple, TYPE_CHECKING, Callable
from pprint import pprint

from agent.core.protocol import LLM_Data
from tools.llm.response_and_chatml_api_client import Response_and_Chatml_LLM_Client
from llm_protocol import LLM_Config
import config
from web_socket_server import Web_Socket_Server_Manager, Web_Socket_Server

DEBUG = True
# DEBUG = config.Global.app_debug

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def dpprint(*args, **kwargs):
    if DEBUG:
        pprint(*args, **kwargs)

# llm工厂
class LLM_Manager:
    llms_dict: Dict[str, LLM_Data]          = {}    # 用于注册全server所有的llms, llm_id <--> llm_data
    web_socket_server:Web_Socket_Server = None

    # 0、用于server管理时的唯一的、必需的启动
    @classmethod
    def init(cls): # 由server侧调用
        # 初始化ws server
        cls.web_socket_server = Web_Socket_Server_Manager.start_server(config.Port.global_llm_socket_server, server_at="llm_manager.py")

    # 1、创建llm，返回llm_id
    @classmethod
    def create_llm(cls, llm_config:LLM_Config)->str:
        llm = Response_and_Chatml_LLM_Client()
        llm.init()
        llm_id = llm.llm_id

        # 注册agent
        llm_data = LLM_Data(
            llm_id=llm_id,
            llm=llm,
        )
        cls.llms_dict[llm_id] = llm_data
        return llm_id

    # 2、启动llm_id下的thread，并run
    @classmethod
    def run_llm(cls, llm_id:str, query):
        llm_data = cls.llms_dict[llm_id]
        llm = llm_data.llm

        llm.

