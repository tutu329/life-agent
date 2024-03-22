import re, json5

DEBUG = True

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)
    else:
        pass

# 解析字符串中的代码块（由于json5无法解析包含'''...'''或"""..."""的字符串，因此通过re抠出'''...'''或"""..."""内容）
def extract_code(text):
    # triple_match1 = re.search(r"'''[^\n]*\n(.+?)'''", text, re.DOTALL)    # 这个不能匹配"""后没有换行的第一行字
    triple_match1 = re.search(r'"""(.+?)"""', text, re.DOTALL)    # 这个能匹配"""后没有换行的第一行字
    # triple_match2 = re.search(r'"""[^\n]*\n(.+?)"""', text, re.DOTALL)    # 这个不能匹配"""后没有换行的第一行字
    triple_match2 = re.search(r'"""(.+?)"""', text, re.DOTALL)    # 这个能匹配"""后没有换行的第一行字
    if triple_match1:
        dprint('extract_code(): triple_matched1.')
        text = triple_match1.group(1)
    elif triple_match2:
        dprint('extract_code(): triple_matched2.')
        text = triple_match2.group(1)
    else:
        dprint('extract_code(): no triple_matched.')
        try:
            text = json5.loads(text)['code']
        except Exception:
            dprint('extract_code(): json5 failed.')
            text = ''

    return text

# 用re把字符串中的最外层{}里的内容抠出来，包含{}
def extract_dict_string(text):
    dprint(f'extract_dict_string(): text = \n"{text}"')
    match = re.search(r'\{.*\}', text, re.DOTALL)
    result = match.group(0) if match else None
    dprint(f'extract_dict_string(): result = \n{result}')
    return result