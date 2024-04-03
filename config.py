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
    llm_url:str = 'http://116.62.63.204:8001/v1'

    # V2Ray代理
    playwright_proxy = {
        "server": "http://127.0.0.1:7890",
    }

    ddgs_proxies = {
        "http": "http://127.0.0.1:7890",
        "https": "http://127.0.0.1:7890",
    }

    ddgs_search_max_num = 50    # ddgs搜索最大数量

@dataclass
class Port():
    # 顶层应用
    flowise:int = 7860
    llm_ui: int = 7861
    fastgpt: int = 7863
    xinference_ui: int = 7870

    # api转发层
    one_api:int = 8002  # flowise等顶层应用可以直接调用:8002/v1的llm_api和m3e_api

    # api底层服务
    # m3e_api:int = 8000  # 由one_api从:8002/v1/embeddings转发到这里
    m3e_api:int = 7870  # 由xinference发布的
    llm_api:int = 8001  # 由one_api从:8002/v1/chat/completions等转发到这里

    milvus_api:int=8003 # milvus单独的api
    chroma_api:int=8004 # chroma单独的api

    # 工作环境
    jupyter:int = 7862
    jupyter_temp:int = 7865  # 自定义jupyter的docker容器
