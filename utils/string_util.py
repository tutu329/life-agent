# str1和str2的交集，且该交集起始和str2起始一致
def _str_has_partial_stop(str, stop):
    same_str = ''
    chunk = ''
    # 找到str1和str2交集
    for ch in stop:
        chunk += ch
        if chunk in str:
            same_str = chunk
            if str.endswith(same_str):
                # print(f'same:"{same_str}"')
                break
        else:
            break

    # 判断partial stop和str1的交集是否为str1尾部，或者完整stop是否in str1
    # print(f'same:"{same_str}"')
    if str.endswith(same_str):
        return same_str
    elif stop in str:
        str = str.split(stop)
        if len(str)>0:
            # 取第一个stop后面所有
            str.pop(0)
            return stop+ ''.join(str)
        else:
            # 原来就没有stop
            str = str[0]
            return str
    else:
        return ''



# "aaaaaaa<stop"和"<stop>"的交集是否为<开始
def _str_remove_partial_stop(str, stop):
    partial_stop = _str_has_partial_stop(str, stop)
    # print(f'partial_stop: "{partial_stop}"')
    if not partial_stop:
        return str
    str = str.split(partial_stop)
    # print(str)
    str.pop()
    # print(str)
    str = partial_stop.join(str)
    # print(str)

    return str

def str_remove_partial_stops(str, stops):
    str1 = str
    # print(f'str: "{str}"')
    min_str = str1
    for stop in stops:
        str1 = _str_remove_partial_stop(str, stop)
        # print(f'str: "{str}", stop: "{stop}"')
        # print(f'mmm: "{min_str}", stop: "{stop}"')
        if len(min_str) > len(str1):
            min_str = str1
        # print(f'str: "{str}", stop: "{stop}"')
    return min_str

def main():
    str1 = "aaaaaaa stopfabc> </stop1[结束<res_stop>【结束<stop>1"
    # str1 = "aaaaaaa stopfabc><stop1<stop1[结束【结束1"
    # str1 = "aaaaaaa stopfabc><stop1<stop1【结束[结束]"
    str2 = "<stop>"
    # str2 = "【结束】"
    stops = ['<stop>', '[结束]', '【结束】', '</s>', '<res_stop>']

    print('str :', str1)  # Output: <stop

    print('fout:', str_remove_partial_stops(str1, stops))


if __name__ == "__main__" :
    main()