import time, threading
import random
import sys
import tiktoken
import json
import traceback
import os

ENCODING = tiktoken.encoding_for_model("gpt-4")

from utils.string_util import get_string_preview
from config import dred, dgreen, dcyan, dblue, dyellow, dblack, dwhite, dmagenta, dlightblack, dlightblue, dlightred, dlightgreen, dlightyellow, dlightcyan, dlightwhite, dlightmagenta
import config

# 颜色复位
RESET = '\033[0m'

# 淡粉红色/灰粉色 ANSI码
LIGHT_PINK = '\033[38;5;217m'  # 淡粉
DUSTY_PINK = '\033[38;5;181m'  # 灰粉
PALE_PINK = '\033[38;5;225m'  # 苍白粉

# 淡灰色 ANSI码
LIGHT_GRAY = '\033[37m'  # 亮灰色
DARK_GRAY = '\033[90m'  # 暗灰色
PALE_GRAY = '\033[38;5;248m'  # 淡灰色
DIM_GRAY = '\033[38;5;242m'  # 暗淡灰

LIGHT_WHITE = '\033[97m'  # 明亮白色
WHITE = '\033[37m'  # 标准白色

LIGHT_BLACK = '\033[90m'    # 明亮黑色
BLACK = '\033[30m'  # 标准黑色

# 绿色系列 ANSI码
LIGHT_GREEN = '\033[92m'  # 明亮绿色
GREEN = '\033[32m'  # 标准绿色
DARK_GREEN = '\033[38;5;22m'  # 深绿色
PALE_GREEN = '\033[38;5;120m'  # 淡绿色
MINT_GREEN = '\033[38;5;156m'  # 薄荷绿
FOREST_GREEN = '\033[38;5;28m'  # 森林绿

# 红色系列 ANSI码
LIGHT_RED = '\033[91m'  # 明亮红色
RED = '\033[31m'  # 标准红色
DARK_RED = '\033[38;5;88m'  # 深红色
PALE_RED = '\033[38;5;210m'  # 淡红色
CRIMSON = '\033[38;5;196m'  # 深红
MAROON = '\033[38;5;52m'  # 栗色

# 蓝色系列 ANSI码
LIGHT_BLUE = '\033[94m'  # 明亮蓝色
BLUE = '\033[34m'  # 标准蓝色
DARK_BLUE = '\033[38;5;18m'  # 深蓝色
PALE_BLUE = '\033[38;5;153m'  # 淡蓝色
SKY_BLUE = '\033[38;5;117m'  # 天蓝色
NAVY_BLUE = '\033[38;5;17m'  # 海军蓝

# 黄色系列 ANSI码
LIGHT_YELLOW = '\033[93m'  # 明亮黄色
YELLOW = '\033[33m'  # 标准黄色
DARK_YELLOW = '\033[38;5;142m'  # 深黄色
PALE_YELLOW = '\033[38;5;230m'  # 淡黄色
GOLD = '\033[38;5;220m'  # 金色
AMBER = '\033[38;5;214m'  # 琥珀色

class Todo_List:
    def __init__(self, title, todo_list):
        self.title = title
        self.todo_list = todo_list
        self.finished_list = [False]*len(self.todo_list)
        self.working_list = [False]*len(self.todo_list)

    def working(self, index):
        if index >= len(self.todo_list) or index < 0:
            return

        self.working_list[index] = True

    def finish(self, index):
        if index >= len(self.todo_list) or index < 0:
            return

        self.finished_list[index] = True

    def print_todo_list(self):
        config.Global.app_debug = True

        # 标题
        dlightgreen('⏺', end='')
        dred(f' {self.title}')

        # todo_list
        i = 0
        for item in self.todo_list:
            if i==0:
                head = '   ⎿ '
            else:
                head = ' ' * 5
            dlightblack(head, end='')

            if self.finished_list[i]:
                # 完成的item
                dlightgreen(f'■ {item}')
            elif self.working_list[i]:
                dlightcyan(f'□ {item}')
            else:
                # 其他item
                dlightblack(f'□ {item}')

            i += 1

        config.Global.app_debug = False

#
# ⏺ Write(index.html)
# ╭─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
# │ Create file                                                                                                         │
# │ ╭─────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮ │
# │ │ index.html                                                                                                      │ │
# │ │ </html>                                                                                                         │ │
# │ ╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯ │
# │ Do you want to create index.html?                                                                                   │
# │ ❯ 1. Yes                                                                                                            │
# │   2. Yes, and don't ask again this session (shift+tab)                                                              │
# │   3. No, and tell Claude what to do differently (esc)                                                               │
# │                                                                                                                     │
# ╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
def print_color():
    tmp_app_debug = config.Global.app_debug
    config.Global.app_debug = True

    dwhite('⏺', end='')
    dlightwhite('⏺', end='')

    dcyan('⏺', end='')
    dlightcyan('⏺', end='')

    dmagenta('⏺', end='')
    dlightmagenta('⏺', end='')

    dyellow('⏺', end='')
    dlightyellow('⏺', end='')

    dgreen('⏺', end='')
    dlightgreen('⏺', end='')

    dblue('⏺', end='')
    dlightblue('⏺', end='')

    dred('⏺', end='')
    dlightred('⏺', end='')

    dblack('⏺', end='')
    dlightblack('⏺')

    config.Global.app_debug = tmp_app_debug

def server_output(info):
    print(f'{LIGHT_BLACK}⏺ {RESET}{LIGHT_RED}{info}{RESET}')

def agent_query_output(query, agent_level=0):
    # print(f'\n{PALE_GRAY}> {query}{RESET}\n')
    query = query.strip().replace('\n', ' ')

    if agent_level==0:
        agent_level_str = ''
    else:
        agent_level_str = '  |   '*agent_level
    print(f'{LIGHT_BLACK}{agent_level_str}{RESET}{PALE_GRAY}> {get_string_preview(query, preview_width=150)}{RESET}')

def agent_thinking_output(answer, output_thinking=False, agent_level=0):
    if not output_thinking:
        return

    answer = answer.strip().replace('\n', ' ')

    agent_level_str = "  "*agent_level + "| "*agent_level + f'{" "*agent_level}'
    print(f'{LIGHT_BLACK}{agent_level_str}{RESET}{LIGHT_GRAY}⏺ {get_string_preview(answer)}{RESET}')

'''
⏺ Web Search("MacBook Air M5 release date 2025")
  ⎿ Found 10 results for "MacBook Air M5 release date 2025"
'''
def agent_tool_chosen_output(tool_name, tool_paras, agent_level=0):
    if isinstance(tool_paras, str):
        tool_paras = json.loads(tool_paras)

    tool_paras_list = []
    for k,v in tool_paras.items():
        tool_paras_list.append(f'{k!r}:{v!r}')
    tool_paras_string = ', '.join(tool_paras_list)

    tool_paras_string = tool_paras_string.replace("\n", " ").strip()

    if agent_level==0:
        agent_level_str = '  |'*agent_level + '  '
    else:
        agent_level_str = '  |   '*agent_level + '  '
    print(f'{LIGHT_BLACK}{agent_level_str}{RESET}{LIGHT_GRAY}⏺ {CRIMSON}{tool_name.strip()}{LIGHT_BLACK}({tool_paras_string}){RESET}')

def agent_tool_result_output(action_result, agent_level=0):
    if isinstance(action_result, str):
        action_result = action_result.replace("\n", " ").strip()

    if agent_level==0:
        agent_level_str = '  |'*agent_level + '  '
    else:
        agent_level_str = '  |   '*agent_level + '  '
    print(f'{LIGHT_BLACK}{agent_level_str}{RESET}{LIGHT_BLACK}⎿ {action_result}{RESET}')

def agent_finished_output(final_answer, agent_level=0):
    if final_answer is None:
        final_answer = ''

    # final_answer = final_answer.strip()
    final_answer = final_answer.replace("\n", " ").strip()

    if agent_level==0:
        agent_level_str = '  |'*agent_level + '  '
    else:
        agent_level_str = '  |   '*agent_level + '  '
    print(f'{LIGHT_BLACK}{agent_level_str}{RESET}{PALE_GREEN}⏺ {LIGHT_BLACK}{final_answer}{RESET}')

def llm_user_output(query):
    print(f'{PALE_GRAY}> {query.strip()!r}{RESET}')

def llm_output(result_gen, think_gen=None):
    # print('■▪▫□◌●◦□└ ┘┌ ┐─│──')
    # 基础星形：
    # ✦ ✧ ✩ ✪ ✫ ✬ ✭ ✮ ✯ ✰ ✱ ✲ ✳ ✴ ✵ ✶ ✷ ✸ ✹ ✺ ✻ ✼ ✽ ✾ ✿ ❀ ❁ ❂ ❃ ❄ ❅ ❆ ❇ ❈ ❉ ❊ ❋
    # 实心星形：
    # ★ ☆ ✦ ✧ ✩ ✪ ✫ ✬ ✭ ✮ ✯ ✰
    # 花形装饰：
    # ❀ ❁ ❃ ❋ ❅ ❆ ❇ ❈ ❉ ❊ ✿ ✾ ✽ ✼ ✻ ✺ ✹ ✸ ✷ ✶ ✵ ✴ ✳ ✲ ✱
    # 多角星：
    # ✢ ✣ ✤ ✥ ✦ ✧ ✨ ✩ ✪ ✫ ✬ ✭ ✮ ✯ ✰ ✱

    # 闪烁字符循环
    blink_chars = ['✽', '✼', '✻', '✲', '✳', '✢', '✳', '✻']
    blink_index = 0

    # 省略号循环
    dots_patterns = ['.', '..', '...']
    dots_index = 0

    # 等待时的随机word
    waiting_words = ['Synthesizing', 'Pontificating']
    waiting_word = random.choice(waiting_words)

    times = 0
    interval = 0.05  # 秒

    result = ''
    finished = False
    tokens_num = 0

    current_full_string = ''
    thinking = False

    def _get_chunk():
        nonlocal result, finished, tokens_num, current_full_string, thinking
        # 统计thinking的大概token数
        if think_gen:
            for chunk in think_gen:
                thinking = True
                current_full_string += chunk
                tokens_num += len(ENCODING.encode(chunk))
        # 统计result的大概token数
        for chunk in result_gen:
            thinking = False
            current_full_string += chunk
            result += chunk
            tokens_num += len(ENCODING.encode(chunk))

        finished = True

    t = threading.Thread(target=_get_chunk)
    t.start()

    buffer = ''
    while not finished:
        # print(chunk, end='', flush=True)
        # result += chunk

        # 获取当前闪烁字符和省略号
        current_char = blink_chars[blink_index % len(blink_chars)]
        current_dots = dots_patterns[dots_index % len(dots_patterns)]

        # 清除当前行并打印新内容
        # ✳ Pontificating… (4s · ↓ 23 tokens · esc to interrupt)
        # buffer += current_chunk
        buffer = current_full_string.replace('\n', ' ')
        buffer = buffer[-30:]
        # print(f'current_full_string: "{current_full_string}"')
        # print(f'buffer: "{buffer}"')
        output = f'[thinking:  {buffer}]' if thinking else f'[outputing: {buffer}]'
        # print(current_full_string, end='', flush=True)
        output_str = f'\r{LIGHT_PINK}{current_char} {waiting_word}{current_dots:<4}{PALE_GRAY}({times * interval:>3.0f}s · ↓ {tokens_num:>4.0f} tokens ) {output}{RESET}     '
        sys.stdout.write(output_str)
        # print(f'len: ({len(output_str)})')
        sys.stdout.flush()

        # 更新
        blink_index += 1
        if times % 10 == 0:
            dots_index += 1

        time.sleep(interval)
        times += 1
    sys.stdout.write(f'\r{LIGHT_PINK}{current_char} {waiting_word}{current_dots:<4}{PALE_GRAY}({times * interval:>3.0f}s · ↓ {tokens_num:>4.0f} tokens ){RESET}{" "*80}')
    sys.stdout.flush()
    # print(f'\n{WHITE}● {RESET}{LIGHT_BLACK}{result}{RESET}\n')
    print(f'\n{LIGHT_WHITE}● {RESET}{BLACK}{result.strip()}{RESET}\n')

def err(e:Exception):
    tb = traceback.extract_tb(e.__traceback__)
    for filename, lineno, func, text in tb:
        abs_path = os.path.abspath(filename)  # 转成绝对路径，IDE 更容易识别
        print(f"{PALE_RED}> File {abs_path}:{lineno} in {func}() \n {text}{RESET}")
    print(f"{DARK_RED}> {e}{RESET}")

def todo_main():
    todo_list = [
        'Create HTML structure for chat page',
        'Add CSS styling for chat interface',
        'Implement JavaScript for chat functionality'
    ]
    l = Todo_List(title='Update Todos', todo_list=todo_list)
    l.working(0)
    l.finish(1)
    # l.working(2)
    l.print_todo_list()

if __name__ == "__main__":
    print_color()
    # todo_main()
