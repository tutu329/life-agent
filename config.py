from dataclasses import dataclass, field

# 用于控制prompt长度的参数
@dataclass
class Prompt_Limitation():
    toc_max_len:int = 4096          # 返回目录(toc)字符串的最大长度
    toc_nonsense_min_len:int = 300  # 返回目录(toc)内容太短从而无法进行总结的长度

    # context_max_len * context_max_paragraphs 为截取后发给llm的文字最大长度，如500*1
    # 例如搜索结果文本的最大分段长度：
    context_max_len:int = 1000      # 返回文本(content)字符串的最大长度 (如果文本超过这个长度，则以该长度为单位，进行分段解读，如context_max_len为500，则600字分为500和100两段)
    summary_max_len:int = 300       # content总结后最大长度(是让llm总结后的长度，llm不一定能完全按要求控制长度)
    # 例如搜索结果文本的最大分段数：
    context_max_paragraphs:int = 6  # 返回文本(content)字符串list的最大长度

@dataclass
class Global():
    line:str = f'{80 * "-"}\n\n'
    llm_url:str = 'http://116.62.63.204:8001/v1'