import threading
import curses
import time

from tools.llm.api_client import LLM_Client



wins = []

def create_window(stdscr, thread_id, win_x, win_y, win_width, win_height):
    # 获取屏幕尺寸
    height, width = stdscr.getmaxyx()

    window = curses.newwin(win_height, win_width, win_y, win_x)
    window.box()
    window.addstr(0, 2, f"窗口 {thread_id+1}")

    window.refresh()
    wins.append(window)

def api_call(stdscr, thread_id, x_position, y_position, width, height):
    llm = LLM_Client(
        # api_key='empty',
        # url='http://localhost:8022/v1',
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        url='https://api.deepseek.com/v1',
    )
    gen  = llm.ask_prepare('你是谁？我的名字是土土', temperature=0.5, max_new_tokens=200).get_answer_generator()
    result = ''

    create_window(stdscr, thread_id, x_position, y_position, width, height)

    for chunk in gen:
        result += chunk

        # 这行代码在linux下正常显示中文，win下不能正常显示中文
        wins[thread_id].addstr(1,2,  f'[{thread_id}] {result}')
        wins[thread_id].refresh()
        # stdscr.addstr(y_position, x_position, f'[{thread_id}] {result}')
        # stdscr.refresh()

def main(stdscr):
    # 禁用光标显示
    curses.curs_set(0)
    # 获取终端尺寸
    device_max_height, device_max_width = stdscr.getmaxyx()
    # 启动多个线程
    threads = []

    max_width = device_max_width // 100 * 100 # 把220变为200
    max_height = device_max_height // 10 * 10 # 把75变为70
    win_width = 100
    win_height = 10

    for i in range(10):  # 假设有10个线程
        x_position = i * win_width % max_width + i * win_width % max_width // win_width + 1
        y_position = i * win_height // ((max_width//win_width)*win_height)* win_height
        t = threading.Thread(target=api_call, args=(stdscr, i, x_position, y_position, 100, 10))
        threads.append(t)
        t.start()
    # 等待所有线程完成
    for t in threads:
        t.join()

    # 等待用户按键退出
    # stdscr.addstr(height - 1, 0, "按任意键退出程序...")
    # stdscr.refresh()
    while True:
        wins[-1].addstr(win_height-1, 2, f"时间: {time.strftime('%H:%M:%S')}")
        wins[-1].refresh()
        time.sleep(0.1)

    stdscr.getch()

if __name__ == "__main__":
    curses.wrapper(main)

