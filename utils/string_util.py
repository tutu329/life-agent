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
好吧，我现在得帮用户解决这个源网荷储项目的优化问题。首先，我得理清楚用户的需求。用户提到这是一个源网荷储项目，年上网电量不超过总发电量的20%，年下网电量不超过总用电量的10%。项目信息包括光伏、风电、储能的单位造价，最大负荷，年用电量，利率，仿真年数等。用户需要找出光伏、风电的最优建设容量以及储能的W和Wh建设容量，并生成报告。

首先，我需要明确用户的问题。用户希望使用提供的工具来计算最优投资规模。工具中有一个energy_investment_plan_tool，正好适用于这种情况。这个工具基于线性规划来优化风光储的投资规模。

接下来，我要整理用户提供的数据，确保所有参数都正确无误地输入到工具中。参数包括基准收益率、仿真年数、最大负荷、年用电量、储能的单位造价、光伏和风电的单位造价，以及是否对光伏和风电进行优化等。

我注意到用户提到年上网电量不超过总发电量的20%，这对应于参数up_flow_max_proportion，应该设置为0.2。同样，年下网电量不超过项目总用电量的10%，对应down_flow_max_proportion，设置为0.1。

然后，我要检查光伏和风电是否需要优化。用户的问题中没有提到已建的光伏和风电规模，因此我假设它们都是0，并且需要优化，所以pv_optimize和wind_optimize都设为true。

现在，我需要将这些参数整理成工具所需的格式。确保所有参数类型正确，特别是布尔值必须用lowercase的true或false。同时，数值单位要正确，比如最大负荷是800MW，转换为kW就是800000kW，年用电量51.2亿kWh等于5120000000kWh。

最后，调用energy_investment_plan_tool，输入所有参数，工具会返回最优的投资规模。如果工具返回的结果符合预期，那么问题就解决了。如果结果不符合，可能需要检查参数是否正确或者是否有其他限制条件未被考虑。
</think>

[思考]
为了回答这个问题，我需要使用能源投资优化系统来计算光伏、风电和储能的最优投资规模。根据用户提供的数据，我需要将这些参数输入到工具中，并让工具进行计算。

[工具]
{
    'tool_invoke': 'yes',
    'tool_name': 'energy_investment_plan_tool',
    'tool_parameters': {
        'rate': 0.08,
        'simu_years': 10,
        'load_max': 800000,  // 转换为kW
        'load_electricity': 5120000000,  // 转换为kWh
        'storage_w_cost': 0.12,
        'storage_wh_cost': 0.83,
        'pv_cost': 3.5,
        'pv_nom0': 0,
        'pv_optimize': true,
        'wind_cost': 3.5,
        'wind_nom0': 0,
        'wind_optimize': true,
        'up_flow_max_proportion': 0.2,
        'down_flow_max_proportion': 0.1
    }
}

<'''
    print(f'--------------s--------------\n"{s}"')
    c = str_remove_content_in_partial_pairs(s, config.LLM_Default.think_pairs)
    print(f'--------------c--------------\n"{c}"')

if __name__ == "__main__" :
    # _main()
    _main_str_remove_content_in_partial_pairs()
