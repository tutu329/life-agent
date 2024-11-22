import threading
import curses
import time

from tools.llm.api_client import LLM_Client

# 模拟API调用的函数
def api_call(stdscr, thread_id, x_position, y_position):
    llm = LLM_Client(
        # api_key='empty',
        # url='http://localhost:8022/v1',
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        url='https://api.deepseek.com/v1',
    )
    gen  = llm.ask_prepare('你是谁？我的名字是土土', temperature=0.5, max_new_tokens=200).get_answer_generator()
    result = ''
    for chunk in gen:
        result += chunk

        # 这行代码在linux下正常显示中文，win下不能正常显示中文
        stdscr.addstr(y_position, x_position, f'[{thread_id}] {result}')
        stdscr.refresh()

def main(stdscr):
    # 禁用光标显示
    curses.curs_set(0)
    # 获取终端尺寸
    height, width = stdscr.getmaxyx()
    # 启动多个线程
    threads = []
    for i in range(5):  # 假设有5个线程
        y_position = i * 10  # 每个线程占用两行
        x_position = 0
        t = threading.Thread(target=api_call, args=(stdscr, i, x_position, y_position))
        threads.append(t)
        t.start()
    # 等待所有线程完成
    for t in threads:
        t.join()
    # 等待用户按键退出
    stdscr.getch()

if __name__ == "__main__":
    curses.wrapper(main)
