from dataclasses import dataclass, field

# 用于控制prompt长度的参数
@dataclass
class Prompt_Limitation():
    toc_max_len:int = 4096          # 返回目录(toc)字符串的最大长度
    toc_nonsense_min_len:int = 300  # 返回目录(toc)内容太短从而无法进行总结的长度
    context_max_len:int = 500       # 返回文本(content)字符串的最大长度 (如果文本超过这个长度，则以该长度为单位，进行分段解读，如600字分为500和100两段)
    context_max_paragraphs:int = 1  # 返回文本(content)字符串list的元素最大数( context_max_len * context_max_paragraphs 为截取后，发给llm的文字最大长度，如500*1)
