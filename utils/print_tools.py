# 输出url和content的内容，如: [https://...]: "..."
def print_long_content_with_urls(in_contents_dict, in_url_len=30, in_content_len=50):
    # in_contents_dict 为 [(url, content_para_list), (url, content_para_list), ...]
    for result in in_contents_dict:
        url = result[0]
        content = '\n'.join(result[1])
        dot1 = '...' if len(url)>in_url_len else ''
        dot2 = '...' if len(content)>in_content_len else ''
        print(f'[{url[:in_url_len]}{dot1}]: "{content[:in_content_len]}{dot2}"')