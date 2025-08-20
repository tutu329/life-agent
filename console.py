import time, threading
import random
import sys
import tiktoken

ENCODING = tiktoken.encoding_for_model("gpt-4")

from colorama import Fore, Style
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

def user_output(query):
    print(f'\n{PALE_GRAY}> {query}{RESET}\n')

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

    current_chunk = ''
    thinking = False

    def _get_chunk():
        nonlocal result, finished, tokens_num, current_chunk, thinking
        # 统计thinking的大概token数
        if think_gen:
            for chunk in think_gen:
                thinking = True
                current_chunk = chunk
                tokens_num += len(ENCODING.encode(chunk))
        # 统计result的大概token数
        for chunk in result_gen:
            thinking = False
            current_chunk = chunk
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
        buffer += current_chunk.replace('\n', ' ')
        buffer = buffer[-30:]
        output = f'[thinking:  {buffer}]' if thinking else f'[outputing: {buffer}]'
        sys.stdout.write(f'\r{LIGHT_PINK}{current_char} {waiting_word}{current_dots:<4}{PALE_GRAY}({times * interval:>3.0f}s · ↓ {tokens_num:>4.0f} tokens ) {output}{RESET}')
        sys.stdout.flush()

        # 更新
        blink_index += 1
        if times % 10 == 0:
            dots_index += 1

        time.sleep(interval)
        times += 1
    sys.stdout.write(f'\r{LIGHT_PINK}{current_char} {waiting_word}{current_dots:<4}{PALE_GRAY}({times * interval:>3.0f}s · ↓ {tokens_num:>4.0f} tokens ){RESET}')
    sys.stdout.flush()
    # print(f'\n{WHITE}● {RESET}{LIGHT_BLACK}{result}{RESET}\n')
    print(f'\n{LIGHT_WHITE}● {RESET}{BLACK}{result.strip()}{RESET}\n')

def llm_main():
    llm_output()

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
    llm_main()