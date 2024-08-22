from enum import Enum, unique
import asyncio
import threading
import time
import signal
import sys

from config import dred, dgreen

@unique
class Status(Enum):
    Created = 0
    Initializing = 1
    Initialized = 2
    Running = 3
    Cancelling = 4
    Cancelled = 5
    Completed = 6

Task_Debug = False

def dprint(*args, **kwargs):
    global Task_Debug
    if Task_Debug:
        print(*args, **kwargs)
    
# Task的接口基类
class Task_Base():
    def __init__(self):
        dprint('Task_Base.__init__()')
        self.inited = False    # 用于singleton实例中，避免重复init
        self.started = False   # 用于singleton实例中，避免重复start
        self.task_info = {}
        self.task_info['status'] = Status.Created    # 为了方便传递引用

        self.task_info['task_name'] = ''
        self.thread = None
        
        self.callback = None
        self.callback_args = None
        self.callback_kwargs = None

        self.timeout_timer = None    # 用于在timeout后设置cancel标识

        self.run_in_streamlit = False

    def terminate(self, in_signal, in_frame):    # in_signal, in_frame 这两个参数是必须要的
        if in_signal==signal.SIGINT:
            dprint(f'\nCtrl+C captured. Main thread terminated.')
            sys.exit(0)

    def init(self, 
             in_callback_func, 
             *in_callback_func_args, 
             in_name='task', 
             in_timeout=None,    # timeout秒之后，设置cancel标识
             in_streamlit=False,
             **in_callback_func_kwargs
            ):
        if not self.inited or (self.inited and self.task_info['status'] == Status.Completed) :
            self.inited = True

            self.run_in_streamlit = in_streamlit
            self.task_info['status'] = Status.Initializing

            self.task_info['task_name'] = in_name

            if threading.current_thread().name == 'MainThread':
                signal.signal(signal.SIGINT, self.terminate)

            dprint(f"{self.task_info['task_name']}.init()")
            self.thread = threading.Thread(target=self.run, daemon=True)    # daemon==True时，主线程退出则该线程也马上退出（可以有效响应ctrl+c）
            if self.run_in_streamlit:
                from streamlit.runtime.scriptrunner import add_script_run_ctx
                add_script_run_ctx(self.thread)

            self.callback = in_callback_func
            self.callback_args = in_callback_func_args
            self.callback_kwargs = in_callback_func_kwargs

            if in_timeout:
                self.timeout_timer = threading.Timer(in_timeout, lambda :self.cancel())

            self.task_info['status'] = Status.Initialized
        else:
            dred(f"Task {self.task_info['task_name']} already initialized and not completed. No more init work done.")
     
    def run(self):
        self.task_info['status'] = Status.Running
        
        dprint(f"{self.task_info['task_name']}.run()")
        
        self.callback(
            self.task_info,     # 注意：这里是返回self.task_info引用，callback从而可以通过task_info['status']等获取信息和状态
            *self.callback_args, 
            **self.callback_kwargs
        )
        
        self.task_info['status'] = Status.Completed

    def start(self):
        # print(f' self.started: { self.started}')
        # print(f"  self.task_info['status']: {  self.task_info['status']}")
        if not self.started or (self.started and self.task_info['status'] == Status.Initialized) :
            self.started = True

            dprint(f"{self.task_info['task_name']}.start()")

            # 启动timeout的timer
            if self.timeout_timer:
                self.timeout_timer.start()

            # 启动task的timer
            self.thread.start()
        else:
            dred(f"Task {self.task_info['task_name']} already started and not completed. No more started.")

    def cancel(self):
        dprint(f"{self.task_info['task_name']}.cancel()")
        self.task_info['status'] = Status.Cancelling

    def join(self):
        self.thread.join()

class Task(Task_Base):
    def __init__(self):
        super().__init__()
        dprint('Task.__init__()')

    def init(self, 
             in_callback_func, 
             *in_callback_func_args, 
             in_name='task', 
             in_timeout=None,    # timeout秒之后，设置cancel标识
             in_streamlit=False,
             **in_callback_func_kwargs
            ):
        super().init(
             in_callback_func, 
             *in_callback_func_args, 
             in_name=in_name, 
             in_timeout=in_timeout,
             in_streamlit=in_streamlit,
             **in_callback_func_kwargs            
        )

    def start(self):
        super().start()

class Flicker_Task(Task_Base):
    def __init__(self, in_stream_buf_callback=None):
        super().__init__()
        self.flicker1 = None
        self.flicker2 = None
        self.flicker = None

        self.flicker_timer = None
        self.interval = None
        self.stopped = False

        self.stream_buf_callback = in_stream_buf_callback

    def init(self, 
             *in_callback_func_args, 
             in_callback_func=None,
             flicker1='█ ', flicker2='  ', interval=1,
             in_name='task', 
             in_timeout=None,    # timeout秒之后，设置cancel标识
             in_streamlit=False,
             **in_callback_func_kwargs
            ):
        super().init(
             in_callback_func, 
             *in_callback_func_args, 
             in_name=in_name, 
             in_timeout=in_timeout,
            in_streamlit=in_streamlit,
             **in_callback_func_kwargs            
        )
        
        self.flicker1 = flicker1
        self.flicker2 = flicker2
        self.flicker = self.flicker1
        self.interval = interval

        return self

    def run(self):
        while True:
            if self.stopped:
                break

            self._stream_output(self.flicker)
            self.__flicker()

            # t = threading.Timer(self.interval, self.__flicker)
            #t.start()
            time.sleep(self.interval)

    def _stream_output(self, in_str):
        if self.stream_buf_callback:
            # 由于streamlit对thread支持不好，这里必须在threading.Thread(target=self.run)之后紧跟调用add_script_run_ctx(t)才能正常调用run()里面的st.markdown()这类功能，不然会报错：missing xxxxContext
            try:
                self.stream_buf_callback(in_str)
            except Exception as e:
                print(f'[Flicker_Task.run()]错误: {e}')
                print('由于streamlit对thread支持不好，须在threading.Thread(target=self.run)之后紧跟调用add_script_run_ctx(t)才能正常调用run()里面的st.markdown()这类功能，不然会报错：missing xxxxContext')

    def start(self):
        super().start()

    def get_flicker(self):
        return self.flicker

    def set_stop(self):
        self.stopped = True
        self._stream_output('')

    def __flicker(self):
        # print(f'================2: {self.flicker}=====================')
        if self.flicker==self.flicker1:
            self.flicker=self.flicker2
        else:
            self.flicker=self.flicker1

def Example_Callback(out_task_info_must_be_here, num):
    i=num
    while True:
        i += 1
        if out_task_info_must_be_here['status']==Status.Cancelling:
             print(f"{out_task_info_must_be_here['task_name']} cancelled")
             break
        print(i)
        time.sleep(1)

def Example_Main():
    t1 = Task_Base()
    t2 = Task()
    t1.init(Example_Callback, in_name='task1', in_timeout=3, num=100)
    t2.init(Example_Callback, in_name='task2', in_timeout=5, num=10000)
    t1.start()
    t2.start()

    f = Flicker_Task()
    f.init(flicker1='█', flicker2='').start()

    while True:
        print(f.get_flicker())
        time.sleep(0.5)

if __name__ == "__main__" :
    Example_Main()
