import re

from wcwidth import wcswidth

import config


def string_right_align(text, width):
    padding = width - wcswidth(text)
    return f"{' ' * padding}{text}" if padding > 0 else text

# 将string后面用pad填充到end
def string_pad_to_end_with_console_width(s, in_width, pad=' '):
    width = 0
    new_string_list = []
    for char in s:
        # 判断是否为中文字符
        if '\u4e00' <= char <= '\u9fff':  # Unicode 范围判断中文
            width += 2
        else:  # 非中文字符，按长度 1 处理
            width += 1

        new_string_list.append(char)

    for w in range(in_width-width):
        new_string_list.append(pad)
    return ''.join(new_string_list)

# 测量string长度 （中文字长度为2，英文字母长度为1，如"Hello世界"长度为9）
def get_console_width_of_string(s):
    width = 0
    for char in s:
        # 判断是否为中文字符
        if '\u4e00' <= char <= '\u9fff':  # Unicode 范围判断中文
            width += 2
        else:  # 非中文字符，按长度 1 处理
            width += 1
    return width

# 获取string前in_console_width宽度的字符串的length长度 （如"Hello世界大同123"前部width为9("Hello世界")的length为7）
def get_length_of_string_head_with_console_width(s, in_console_width):
    console_width = 0
    length = 0
    for char in s:
        # 判断是否为中文字符
        if '\u4e00' <= char <= '\u9fff':  # Unicode 范围判断中文
            console_width += 2
        else:  # 非中文字符，按长度 1 处理
            console_width += 1

        length += 1
        if console_width >= in_console_width:
            return length

    return length

# str1和str2的交集，且该交集起始和str2起始一致
def _str_has_partial_substr(str, substr):
    same_str = ''
    chunk = ''
    # 找到str1和str2交集
    for ch in substr:
        chunk += ch
        if chunk in str:
            same_str = chunk
            if str.endswith(same_str):
                # print(f'same:"{same_str}"')
                break
        else:
            break


    # 判断partial substr和str1的交集是否为str1尾部，或者完整substr是否in str1
    # print(f'same:"{same_str}"')
    if str.endswith(same_str):
        return same_str
    elif substr in str:
        str = str.split(substr)
        if len(str)>0:
            # 取第一个stop后面所有
            str.pop(0)
            return substr+ ''.join(str)
        else:
            # 原来就没有stop
            str = str[0]
            return str
    else:
        return ''



# "aaaaaaa<stop"和"<stop>"的交集是否为<开始
def _str_remove_partial_substring(str, substr):
    partial_substr = _str_has_partial_substr(str, substr)
    # print(f'partial_stop: "{partial_stop}"')
    if not partial_substr:
        return str
    str = str.split(partial_substr)
    # print(str)
    str.pop()
    # print(str)
    str = partial_substr.join(str)
    # print(str)

    return str

# str_remove_partial_substring('string12[观', ['[观察]']) -> 'string12'
# str_remove_partial_substring('string12[观察]34', ['[观察]']) -> 'string12'
def str_remove_partial_substring(str, substrings):
    str1 = str
    # print(f'str: "{str}"')
    min_str = str1
    for substr in substrings:
        str1 = _str_remove_partial_substring(str, substr)
        # print(f'str: "{str}", stop: "{stop}"')
        # print(f'mmm: "{min_str}", stop: "{stop}"')
        if len(min_str) > len(str1):
            min_str = str1
        # print(f'str: "{str}", stop: "{stop}"')
    return min_str


# str_get_content_in_partial_pairs('string12<think>1112</thin', ('<think>', '</think>'))       -> '1112'
# str_get_content_in_partial_pairs('string12<think>1112</think>3456', ('<think>', '</think>')) -> '1112'
def _str_get_content_in_partial_pairs(str, pairs):
    # 'string12<think>1112</think>3456'
    str_left_and_content = _str_remove_partial_substring(str, pairs[1])     # 'string12<think>1112'
    # print(f'1) str_left_and_content: \n"{str_left_and_content}"')

    if pairs[0] in str:
        str_left = str.split(pairs[0])[0]
    else:
        str_left = _str_remove_partial_substring(str, pairs[0])             # 'string12'
    # print(f'2) str_left: \n"{str_left}"')

    pair1_and_content = str_left_and_content.replace(str_left, '')    # '<think>1112'
    # print(f'3) pair1_and_content: \n"{pair1_and_content}"')

    rtn_str = pair1_and_content.replace(pairs[0], '')                 # '1122'
    # print(f'4) rtn_str: \n"{rtn_str}"')

    return rtn_str


# str_get_content_in_partial_pairs('string12<think>1112</thin', ('<think>', '</think>'))       -> 'string12'
# str_get_content_in_partial_pairs('string12<think>1112</think>3456', ('<think>', '</think>')) -> 'string123456'
def str_remove_content_in_partial_pairs(str, pairs):
    # print(f'-----0) str-----\n"{str}"')

    content = _str_get_content_in_partial_pairs(str, pairs)
    # print(f'-----1) content-----\n"{content}"')

    rtn_str = str.replace(content, '')
    # print(f'-----2) rtn_str-----\n"{rtn_str}"')

    rtn_str = rtn_str.replace(pairs[1], '')
    # print(f'-----3) rtn_str-----\n"{rtn_str}"')

    rtn_str = rtn_str.replace(pairs[0], '')
    # print(f'-----4) rtn_str-----\n"{rtn_str}"')

    rtn_str = _str_remove_partial_substring(rtn_str, pairs[1])
    # print(f'-----5) rtn_str-----\n"{rtn_str}"')
    # print(f'--------------------')
    return rtn_str

def str_replace_multiple_newlines_with_one_newline(text):
    return re.sub(r'\n{2,}', '\n', text)

def _main():
    # str1 = "['search_tool','code_tool','energy_investment_plan_tool','qa_url_content_tool'] 。aaaaaaa 'search_tool' stopfabc> </stop1[结束<res_stop>【结束<stop>1"
    # str1 = "['search_tool', 'code_tool', 'energy_investment_plan_tool', 'qa"
    str1 = "aaaaaaa stopfabc><stop1<stop1【结束[结束]"
    # str2 = "<stop>"
    # str2 = "【结束】"
    # str2 = "[结束]"
    stops = ['<stop>', '[结束]', '【结束】', '</s>', '<res_stop>']
    # stops = ['<|im_end|>', '<|im_start|>', '<s>', '</s>', '<step>', '<结束>']

    print('str :', str1)  # Output: <stop

    print('fout:', str_remove_partial_substring(str1, stops))

def _main_str_remove_content_in_partial_pairs():
    s = '''<think>
Okay, so I need to figure out what the capital of China is. Hmm, I remember from school that China's capital is Beijing. But wait, let me think again to make sure I'm not mixing it up with another country. Sometimes I get confused between different countries' capitals. For example, I know that the capital of Canada is Ottawa, and the capital of the United States is Washington, D.C. So, for China, it's definitely Beijing. I think it's been the capital for a long time, maybe even centuries. I recall that Beijing was also known as Peking in the past. Yeah, that sounds right. So, I'm pretty confident that the answer is Beijing.
</think>

The capital of China is Beijing.
'''
    print(f'--------------s--------------\n"{s}"')
    c = str_remove_content_in_partial_pairs(s, config.LLM_Default.think_pairs)
    print(f'--------------c--------------\n"{c}"')

if __name__ == "__main__" :
    # _main()
    _main_str_remove_content_in_partial_pairs()
