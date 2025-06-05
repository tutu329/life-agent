import time
import functools
from typing import Any, Callable
from config import dred, dgreen, dblue, dcyan, dyellow

# def timer(func):
#     def wrapper(*args, **kwargs):
#         start_time = time.time()
#         result = func(*args, **kwargs)
#         end_time = time.time()
#         time_str = f'{end_time - start_time:.2f}'
#         dgreen(f'{func.__name__}() finished in {time_str} seconds.')
#         return result
#     return wrapper
#
#


def timer(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        # 判断是类方法还是实例方法
        if args and hasattr(args[0], '__name__'):
            class_name = args[0].__name__
        elif args and hasattr(args[0].__class__, '__name__'):
            class_name = args[0].__class__.__name__
        else:
            class_name = "Unknown"

        dyellow(f"【{class_name}.{func.__name__} 执行时间: {end_time - start_time:.4f} 秒】")
        return result

    return wrapper

def main():
    @timer
    def my_function(n, x=2, y=3):
        time.sleep(n)
        print(f'x:{x}, y:{y}')
        return "Done"
    my_function(3)

if __name__ == "__main__" :
    main()