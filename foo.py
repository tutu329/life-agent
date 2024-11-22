import threading
import curses
import time

# 模拟API调用的函数
def api_call(stdscr, thread_id, y_position):
    for i in range(10):
        # 模拟API返回的流式数据
        result = f"Thread {thread_id} - Data {i}"
        # 在指定位置输出结果
        stdscr.addstr(y_position, 0, result)
        stdscr.refresh()
        time.sleep(1)  # 模拟延迟

def main(stdscr):
    # 禁用光标显示
    curses.curs_set(0)
    # 获取终端尺寸
    height, width = stdscr.getmaxyx()
    # 启动多个线程
    threads = []
    for i in range(5):  # 假设有5个线程
        y_position = i * 2  # 每个线程占用两行
        t = threading.Thread(target=api_call, args=(stdscr, i, y_position))
        threads.append(t)
        t.start()
    # 等待所有线程完成
    for t in threads:
        t.join()
    # 等待用户按键退出
    stdscr.getch()

if __name__ == "__main__":
    curses.wrapper(main)
