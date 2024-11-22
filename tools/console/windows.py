import threading
import curses
import time
from dataclasses import dataclass, field
from utils.string_util import calculate_length

@dataclass
class Win_Data:
    thread_id:int = None
    output_buf:object = None
    win_obj:object = None

class Console_Windows:
    def __init__(self):
        self.stdscr = None
        self.user_callback = None

        self.screen_max_width = None
        self.screen_max_height = None

        self.win_height = None
        self.win_width = None
        self.win_number = None

        self.windows_dict = None

    def init(
            self,
            stdscr,         # curses.wrapper(main)传入main(stdscr)的stdscr
            user_callback,   # 回调函数win_callback(thread_id, window)
            win_height=10,
            win_width=100,
            win_number=10,
    ):
        self.stdscr = stdscr
        self.user_callback = user_callback

        self.win_height = win_height
        self.win_width = win_width
        self.win_number = win_number

        self.windows_dict = {}

        self.screen_max_height, self.screen_max_width = self.stdscr.getmaxyx()

    def start(self):
        # 禁用光标显示
        self.stdscr.clear()
        curses.curs_set(0)

        max_width = self.screen_max_width // self.win_width * self.win_width        # 把220变为200
        max_height = self.screen_max_height // self.win_height * self.win_height    # 把75变为70

        # 创建多个window
        for i in range(self.win_number):  # 假设有10个线程
            x_position = i * self.win_width % max_width + i * self.win_width % max_width // self.win_width + 1
            y_position = i * self.win_height // ((max_width // self.win_width) * self.win_height) * self.win_height
            self._create_window(i, x_position, y_position, self.win_width, self.win_height)

        # time.sleep(1) # 等待create_window完成渲染

        # 启动callback任务
        threads = []
        for i in range(self.win_number):  # 假设有10个线程
            t = threading.Thread(target=self._run_window, args=(i,))
            threads.append(t)
            t.start()

        # 等待所有任务完成
        for t in threads:
            t.join()

        # 这里不增加循环直接推出，似乎直接清屏看不到结果
        while True:
            time.sleep(0.1)

        # 等待用户按键退出
        # self.stdscr.addstr(height - 1, 0, "按任意键退出程序...")
        self.stdscr.refresh()
        self.stdscr.getch()

    # 创建一个window
    def _create_window(self, thread_id, win_x, win_y, win_width, win_height):
        window = curses.newwin(win_height, win_width, win_y, win_x)
        window.box()

        def _win_output_buf(content, caption=''):
            window.addstr(0, 2, f"窗口 {thread_id + 1}: {caption}")      # 输出window标题

            # # 检测文本总长是否超限
            # start = len(content)-(self.win_height*self.win_width/2-self.win_height*2/2)
            # start = start if start>0 else 0
            #
            # # 检测行数是否超限
            # lines_num = len(content.split('\n'))
            # line_start = lines_num-(self.win_height-2)
            # line_start = line_start if line_start>0 else 0
            # content = '\n'.join(content.split('\n')[line_start:])

            try:
                # 按\n分为多个line
                output_lines = []
                content_list = content.split('\n')

                # 每一个line进行处理
                for line in content_list:
                    long_line = line

                    # 一行长文->多行文字
                    while(calculate_length(long_line)>self.win_width-50):
                        output_lines.append(long_line[:self.win_width-50])
                        long_line = long_line[self.win_width-50:]
                    output_lines.append(long_line)

                # 此时output_lines为自动换行的文字
                # 将行数超限的内容去掉
                lines_num = len(output_lines)
                line_start = lines_num - (self.win_height - 2)
                line_start = line_start if line_start > 0 else 0
                output_lines = output_lines[line_start:]

                # 按行print
                for i, line in enumerate(output_lines):
                    window.addstr(i+1, 2, line)                        # 按最大量输出，超过后滚动输出

            except Exception as e:
                pass

            window.refresh()

        # 创建一个win_data
        win_data = Win_Data(thread_id=thread_id, output_buf=_win_output_buf, win_obj=window)
        # 将本窗口的win_data按照id注册
        self.windows_dict[thread_id] = win_data

    # 运行一个window，
    # 并提供回调参数win_obj
    #   win_obj.thread_id
    #   win_obj.output_buf
    # 方便回调者获得id和输出buf
    def _run_window(self, thread_id):
        # 查询window在dict中对应的win_data
        win_data = self.windows_dict[thread_id]

        # windo调用user_callback
        self.user_callback(win_data)

        # window刷新
        win_data.win_obj.refresh()

def main(stdscr):
    from tools.llm.api_client import LLM_Client

    def user_callback(win_data):
        llm = LLM_Client(
            # api_key='empty',
            # url='http://powerai.cc:8022/v1',
            api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
            url='https://api.deepseek.com/v1',
        )
        gen = llm.ask_prepare('选取一首李白的诗，将诗的名字返回给我', temperature=0.01, max_new_tokens=200).get_answer_generator()

        res = ''
        caption = f'temp={0.03}'
        for chunk in gen:
            res += chunk
            win_data.output_buf(content=res, caption=caption)

        # while True:
        #     content = f'这是window[{win_obj.thread_id}], 时间: {time.strftime("%H:%M:%S")}'
        #     win_obj.output_buf(content)
        #     time.sleep(0.1)

    console = Console_Windows()
    console.init(stdscr=stdscr, user_callback=user_callback)
    console.start()

if __name__ == "__main__":
    curses.wrapper(main)