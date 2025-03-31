from agent.mem.mem_0 import Mem_0

class Mem_Manager():
    _instance = None

    @classmethod
    def get_singleton_mem(cls, mem_class):
        if cls._instance is None:
            cls._instance = mem_class()
            cls._instance.init()
        return cls._instance

def main():
    mem1 = Mem_Manager.get_singleton_mem(Mem_0)
    mem2 = Mem_Manager.get_singleton_mem(Mem_0)

    print(mem1.id)
    print(mem2.id)
    mem1.get_related_memories(question='我是谁？')

if __name__ == "__main__":
    main()