from dataclasses import dataclass, field

# 用于控制prompt长度的参数
@dataclass
class Prompt_Limitation():
    toc_max_len:int = 4096          # 返回目录(toc)字符串的最大长度
    toc_nonsense_min_len:int = 300  # 返回目录(toc)内容太短从而无法进行总结的长度
    context_max_len:int = 500       # 返回文本(content)字符串的最大长度
    context_max_paragraphs:int = 1  # 返回文本(content)字符串list的元素最大数，>1
    # context_max_len:int = 5000      # 返回文本(content)字符串的最大长度
    # context_max_len:int = 8192      # 返回文本(content)字符串的最大长度