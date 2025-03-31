from agent.mem.mem_base import Mem_Base

class Mem_Manager():
    _instance = None

    @classmethod
    def get_singleton_mem(cls, mem_class):
        if cls._instance is None:
            cls._instance = mem_class()
        return cls._instance


class _Mem_Child_Test(Mem_Base):
    def __init__(self):
        super().__init__()

    def init(self):
        pass

def main():
    mem1 = Mem_Manager.get_singleton_mem(_Mem_Child_Test)
    mem2 = Mem_Manager.get_singleton_mem(_Mem_Child_Test)

    print(mem1.id)
    print(mem2.id)

if __name__ == "__main__":
    main()