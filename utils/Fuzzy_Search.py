# pip install fuzzywuzzy
# pip install python-Levenshtein

from fuzzywuzzy import fuzz

# 简单匹配
# 最常用的模糊比较，返回0-100的相似度
# string1 = "Hello World"string2 = "Hello, World!"similarity_ratio = fuzz.ratio(string1, string2)print(similarity_ratio) # 83
def like_match(a, b):
    return fuzz.ratio(a, b)

# 部分匹配
# string1 = "Hello World"string2 = "Hello, World!"partial_similarity_ratio = fuzz.partial_ratio(string1, string2)print(partial_similarity_ratio) # 100
def partial_match(a, b):
    return fuzz.partial_ratio(a, b)

# 仅匹配单词
# string1 = "Hello World"
# string2 = "World Hello"
# token_sort_similarity_ratio = fuzz.token_sort_ratio(string1, string2)
# print(token_sort_similarity_ratio) # 100
def token_sort_ratio(a, b):
    return fuzz.token_sort_ratio(a, b)

# 仅匹配单词
# string1 = "Hello World"
# string2 = "World Hello"
# token_set_similarity_ratio = fuzz.token_set_ratio(string1, string2)
# print(token_set_similarity_ratio) # 100
def token_set_ratio(a, b):
    return fuzz.token_set_ratio(a, b)

# 处理大量数据1
# string1 = "Hello World"
# string2 = "World Hello"
# WRatio_similarity_ratio = fuzz.WRatio(string1, string2)
# print(WRatio_similarity_ratio) # 100
def wratio(a, b):
    return fuzz.WRatio(a, b)

# 处理大量数据2
# string = "Hello World"
# string_list = ["World Hello", "Hello Universe", "Hello World"]
# extracted_strings = process.extractBests(string, string_list, score_cutoff=70)
# print(extracted_strings)
# [('Hello World', 100), ('World Hello', 100)]
def extract_bests(a, b, score_cutoff=70):
    return fuzz.extractBests(a, b, score_cutoff=score_cutoff)

if __name__ == "__main__":
    print(wratio('Chapter 1. Overview and key findings', '根据目录结构，该文档的总体内容描述应该在"Chapter 1. Overview and key findings"这一章节中'))