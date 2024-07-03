from dataclasses import dataclass, field
from colorama import Fore, Back, Style

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

    llm_url:str = 'http://192.168.124.33:8001/v1/'
    llm_max_new_tokens:int = 1024
    llm_temperature:float = 0.7
    # llm_url:str = 'http://116.62.63.204:8001/v1'
    llm_key:str = 'empty'
    llm_model:str = None
    # llm_url:str = 'https://api.deepseek.com'
    # llm_key:str = 'sk-c1d34a4f21e3413487bb4b2806f6c4b8'
    # llm_model:str = 'deepseek-chat'

    # llm_url2:str = 'http://192.168.124.33:8000/v1'
    # llm_key2:str = 'empty'
    # llm_model2:str = None

    # llm_system:str = "你是甄嬛。"
    # llm_system:str = "你是一个助理。"
    llm_system_prompt:str = "You are a helpful assistant."

    comfy_url:str = 'http://localhost:5100'


    redis_proxy_server_sleep_time:float = 0.05    # redis task server循环的sleep时间

    # V2Ray代理
    playwright_proxy = {
        "server": "http://127.0.0.1:10809", # windows
        # "server": "http://127.0.0.1:7890",
    }
    playwright_get_url_content_time_out = 3000          # 超时设置ms
    playwright_url_content_not_needed = ['\xa0', '']    # 获取url内容时，不需要的内容

    ddgs_proxies = {
        "http": "http://127.0.0.1:7890",
        "https": "http://127.0.0.1:7890",
    }

    ddgs_search_max_num = 50    # ddgs搜索最大数量

    work_dir = '/home'   # 工作目录
    temp_dir = './temp'

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
    xinference_ui: int  = 7870

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
    redis:int=8010              # redis消息服务

    # 工作环境
    jupyter:int         = 7862
    open_webui:int      = 7864  # open-webui
    jupyter_temp:int    = 7865  # 自定义jupyter的docker容器
    # sd:int              = 7868  # stable diffusion
    # comfy:int           = 7869  # ComfyUI
    comfy:int           = 5100  # ComfyUI
