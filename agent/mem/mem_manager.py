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
    from pprint import pprint

    mem1 = Mem_Manager.get_singleton_mem(Mem_0)
    mem2 = Mem_Manager.get_singleton_mem(Mem_0)

    print(mem1.id)
    print(mem2.id)
    messages = [
        {"role": "user", "content": "我叫土土"},
        {"role": "assistant", "content": "你好，土土，很高兴认识你！"},
        {"role": "user", "content": "我家在杭州"},
        {"role": "assistant", "content": "杭州是个很美丽的地方！"}
    ]

    res = mem1.add_mem(user_id='tutu', messages=messages)
    print(f'res: {res!r}')
    res = mem1.get_related_memories(question='我是谁？', user_id='tutu')
    pprint(res)

    res = mem1.get_all_memories(user_id='tutu')
    pprint(res)


if __name__ == "__main__":
    main()