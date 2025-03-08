import socket, requests

from dataclasses import dataclass, field
from colorama import Fore, Back, Style
from typing import Dict, List, Optional, Any

import platform

def get_os():
    os_name = platform.system()
    if os_name == "Linux":
        # 进一步检查是否是Ubuntu
        with open("/etc/os-release") as f:
            if "ID=ubuntu" in f.read():
                return "ubuntu"
        return "linux"
    elif os_name == "Windows":
        return "windows"
    else:
        return "unknown"

def get_local_ip():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return local_ip

def get_public_ip():
    try:
        response = requests.get('https://powerai.cc')
        response.raise_for_status()  # 如果响应状态码不是200，抛出异常
        data = response.json()
        return data['ip']
    except requests.RequestException as e:
        print(f"Error fetching public IP: {e}")
        return None

def get_hostname():
    hostname = socket.gethostname()
    return hostname

def _dcolor(in_color, *args, **kwargs):
    print(in_color, end='', flush=True)
    print(*args, **kwargs)
    print(Style.RESET_ALL, end='', flush=True)

def dred(*args, **kwargs):
    _dcolor(Fore.RED, *args, **kwargs)
def dgreen(*args, **kwargs):
    _dcolor(Fore.GREEN, *args, **kwargs)
def dblue(*args, **kwargs):
    _dcolor(Fore.BLUE, *args, **kwargs)
def dcyan(*args, **kwargs):
    _dcolor(Fore.CYAN, *args, **kwargs)

def dyellow(*args, **kwargs):
    _dcolor(Fore.YELLOW, *args, **kwargs)

# 用于控制prompt长度的参数
@dataclass
class Prompt_Limitation():
    toc_max_len:int = 4096          # 返回目录(toc)字符串的最大长度
    toc_nonsense_min_len:int = 300  # 返回目录(toc)内容太短从而无法进行总结的长度

    # context_max_len * context_max_paragraphs 为截取后发给llm的文字最大长度 (qwen1.5-72b-int4下(--max-model-len=13000 --max-num-seqs=4), 3000*4=12,000容易oom, 但是1000*26=26,000可以)
    # 例如搜索结果文本的最大分段长度：
    concurrent_para_max_len:int = 28000             # 返回文本(content)字符串的最大长度 (如果文本超过这个长度，则以该长度为单位，进行分段解读，如context_max_len为500，则600字分为500和100两段)
    concurrent_para_max_len_in_search:int = 1000
    # 例如搜索结果文本的最大分段数：
    concurrent_max_paras:int = 1                    # 返回文本(content)字符串list的最大长度

    concurrent_summary_max_len:int = 1000       # content总结后最大长度(是让llm总结后的长度，llm不一定能完全按要求控制长度)

@dataclass
class Global():
    line:str = f'{80 * "-"}\n\n'
    llm_max_chat_turns = 200    # 对话超过llm_max_chat_turns轮，则pop最前面的对话

    llm_max_new_tokens:int = 1024
    llm_temperature:float = 0.7
    # llm_url:str = 'http://116.62.63.204:8001/v1'
    llm_key:str = 'empty'
    llm_model:str = None
    # llm_url:str = 'https://api.deepseek.com'
    # llm_key:str = 'sk-c1d34a4f21e3413487bb4b2806f6c4b8'
    # llm_model:str = 'deepseek-chat'

    # llm_system_prompt:str = "你是甄嬛。"
    # llm_system_prompt:str = "你是一个助理。"
    llm_system_prompt:str = "You are a helpful assistant."

    redis_proxy_server_sleep_time:float = 0.05    # redis task server循环的sleep时间

    # V2Ray代理
    playwright_proxy = {
        "server": "http://127.0.0.1:10809", # windows
        # "server": "http://127.0.0.1:7890",
    }

    if get_os()=='windows':
        playwright_user_agent = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
    elif get_os() == 'linux' or get_os() == 'ubuntu':
        playwright_user_agent = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    playwright_headless: bool = True
    playwright_goto_page_time_out = 2000            # search或者打开一个page的超时设置ms
    playwright_bing_search_max_retry = 10           # legacy: 超时retry次数，主要解决chrome打开bing.com后卡死问题
    playwright_get_all_urls_content_time_out = 5000 # 并发打开多个页面获取结果的总超时设置ms
    concurrent_contents_qa_length_limit = 5000      # 设置并发QA长文档的单个文档长度，以8卡qwen2.5-72b-int4为考虑

    html_main_text_tags = [
        'p', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        # 'p', 'span', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    ]
    html_text_tags = [
        'div', 'p', 'span', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'strong', 'em', 'b', 'i', 'u', 'small', 'mark', 'del', 'ins',
        'sup', 'sub', 'blockquote', 'q', 'cite', 'abbr', 'code', 'pre',
        'li', 'dt', 'dd', 'summary', 'label', 'legend', 'figcaption'
    ]

    ddgs_proxies = {
        "http": "http://127.0.0.1:7890",
        "https": "http://127.0.0.1:7890",
    }

    ddgs_search_max_num = 50    # ddgs搜索最大数量

    work_dir = '/home'   # 工作目录
    temp_dir = './temp'
    api_dir = './custom_command/t2i/api'

    @staticmethod
    def get_work_dir():
        import os
        return os.path.abspath(os.curdir)


@dataclass
class Port():
    # 顶层应用
    flowise:int         = 7860
    llm_ui: int         = 7861
    fastgpt: int        = 7863
    dify: int           = 7866
    sovit: int          = 7867
    openwebui: int      = 7870
    ragflow: int        = 7871

    # api转发层
    one_api:int = 8002  # flowise等顶层应用可以直接调用:8002/v1的llm_api和m3e_api

    # api底层服务
    m3e_api:int = 7870  # 由xinference发布的

    llm_api0:int = 8000  # vllm
    llm_api1:int = 8001  # vllm
    llm_api2:int = 8002  # vllm

    milvus_api:int=8003 # milvus单独的api
    chroma_api:int=8004 # chroma单独的api

    redis_monitor:int=8009      # redis monitor
    redis_client:int=8010              # redis消息服务

    # 工作环境
    jupyter:int         = 7862
    open_webui:int      = 7864  # open-webui
    jupyter_temp:int    = 7865  # 自定义jupyter的docker容器
    # sd:int              = 7868  # stable diffusion
    # comfy:int           = 7869  # ComfyUI
    llm_viz:int         = 7869  # 三维演示gpt结构
    comfy:int           = 5100  # ComfyUI

@dataclass
class Domain():
    # 用于redis、streamlit的ssl证书文件path
    if get_os()=='windows':
        ssl_keyfile:str = 'd:\\models\\powerai.key'
        ssl_certfile:str = 'd:\\models\\powerai_public.crt'
    elif get_os()=='ubuntu':
        ssl_keyfile:str = '/home/tutu/ssl/powerai.key'
        ssl_certfile:str = '/home/tutu/ssl/powerai_public.crt'
    elif get_os()=='linux':
        ssl_keyfile:str = '/home/tutu/ssl/powerai.key'
        ssl_certfile:str = '/home/tutu/ssl/powerai_public.crt'

    server_domain:str = 'powerai.cc'
    # win
    llm_url:str = f'https://{server_domain}:{Port.llm_api1}/v1'
    # llm_url:str = 'https://172.27.67.106:8001/v1'
    redis_server_domain:str = server_domain





    comfyui_server_domain:str = f'powerai.cc:{Port.comfy}'

    # ubuntu
    # llm_url:str = 'http://192.168.124.33:8001/v1/'
    # redis_server_ip:str = '192.168.124.33'
    # redis_server_port:int = 8010

@dataclass
class LLM_Default:
    temperature:float   = 0.6
    max_new_tokens:int  = 2048
    # stop:List[str]      = field(default_factory=list)
    stream:int         = 1          # 注意这里不能用bool，因为经过redis后，False会转为‘0’, 而字符‘0’为bool的True
    history:int        = 1          # 注意这里不能用bool，因为经过redis后，False会转为‘0’, 而字符‘0’为bool的True
    clear_history:int  = 0          # 用于清空history_list, 注意这里不能用bool，因为经过redis后，False会转为‘0’, 而字符‘0’为bool的True
    api_key:str         = 'empty'
    url:str             = Domain.llm_url

    think_pairs: tuple  = ('<think>', '</think>')

def main():
    os = get_os()
    print(os)
    print(f'ssl_key: {Domain.ssl_keyfile}')
    print(f'ssl_cert: {Domain.ssl_certfile}')

if __name__ == "__main__":
    main()