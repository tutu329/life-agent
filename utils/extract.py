import re, json5

DEBUG = False
# DEBUG = True

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

def get_ajs_anonymous_id_from_cookie(cookie_str):
    cookies = {}
    parts = cookie_str.split(';')
    id = parts[0].strip().split('=')[1]
    return id

def main():
    s = 'ajs_anonymous_id=c69bf22c-4913-4538-a723-296d45b8757d; _xsrf=2|0a60d08c|4a40a946db36563418dfec6e53cc295e|1709987858; username-116-62-63-204-7865="2|1:0|10:1711016544|27:username-116-62-63-204-7865|200:eyJ1c2VybmFtZSI6ICIyMmViNTQ5ODMwMGY0ZGM1YWIyZDRlYWNiNzU4YjdjYyIsICJuYW1lIjogIkFub255bW91cyBBZHJhc3RlYSIsICJkaXNwbGF5X25hbWUiOiAiQW5vbnltb3VzIEFkcmFzdGVhIiwgImluaXRpYWxzIjogIkFBIiwgImNvbG9yIjogbnVsbH0=|7d91f54c18bf2e533cd287a93e7dfd5cf4ee9142d015a19c175f2b936e4e3a3a"; session=MTcxMTAxNzY0NXxEWDhFQVFMX2dBQUJFQUVRQUFCc180QUFCQVp6ZEhKcGJtY01CQUFDYVdRRGFXNTBCQUlBQWdaemRISnBibWNNQ2dBSWRYTmxjbTVoYldVR2MzUnlhVzVuREFZQUJISnZiM1FHYzNSeWFXNW5EQVlBQkhKdmJHVURhVzUwQkFNQV84Z0djM1J5YVc1bkRBZ0FCbk4wWVhSMWN3TnBiblFFQWdBQ3zKB667wtI3RcRWzTSlSqmQoitlGPMK5TEqkA8XG51p7A==; username-116-62-63-204-7862=2|1:0|10:1712619135|27:username-116-62-63-204-7862|196:eyJ1c2VybmFtZSI6ICIzNTJjOWY3MTAzOTc0NmVkYjAxZGI5NWY5MGM4NzNhOCIsICJuYW1lIjogIkFub255bW91cyBJb2Nhc3RlIiwgImRpc3BsYXlfbmFtZSI6ICJBbm9ueW1vdXMgSW9jYXN0ZSIsICJpbml0aWFscyI6ICJBSSIsICJjb2xvciI6IG51bGx9|a9bd90a09a2a9f4c1f97361c9e4fc64c86839d4dddf094ce8f6fc751f7d455e2; X-CSRF-Token=9d59265255c86c992fcb5a97a0f6ea2f204ef8302c73386ad0ba5d1e140f9e3c'
    cookie = get_ajs_anonymous_id_from_cookie(s)
    print(cookie)

if __name__ == "__main__" :
    main()