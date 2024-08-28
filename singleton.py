import threading

def singleton(cls):
    instances = {}
    lock = threading.Lock()

    def get_instance(*args, **kwargs):
        with lock:
            if cls not in instances:
                instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance

# 示例类
@singleton
class SingletonClass:
    def __init__(self):
        pass

# 测试
if __name__ == "__main__":
    obj1 = SingletonClass()
    obj2 = SingletonClass()

    print(obj1 is obj2)  # True

