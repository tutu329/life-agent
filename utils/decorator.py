import time

from config import dred, dgreen, dblue, dcyan

def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        time_str = f'{end_time - start_time:.2f}'
        dred(f'{func.__name__}() finished in {time_str} seconds.')
        return result
    return wrapper

def main():
    @timer
    def my_function(n):
        time.sleep(n)
        return "Done"
    my_function(3)

if __name__ == "__main__" :
    main()