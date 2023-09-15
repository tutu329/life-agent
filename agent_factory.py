import time, random, datetime
from threading import Thread

from gpu_server.Openai_Api_for_Qwen import *
from gpu_server.Stable_Diffusion import *

# =============================== LLM接口 =================================
# def ask_llm_with_history(user_input, his=[]):
#     return ask(user_input=user_input, his=his)

# 此Agent为异步为主方案，即不以同步完成user的任务为第一目标
class Base_Agent():

    # agent的构造
    def __init__(self, in_agent_id):
        # ===========================特殊属性===============================
        self.end_char = Agent_Factory.agent_config['debug_end_char']
        self.test_llm = None
        # ===========================基本属性===============================
        # ID
        self.agent_id = in_agent_id
        # 属性
        self.property = {
            'name':'',
            'nick':'',
            'gender':'',
        }
        # 状态
        self.status = {
            'hp': '',
            'age': '',
            'health': '',
        }
        # 线程
        self.thread = None

        # ===========================高阶属性===============================
        # 自由意志
        self.mind = None
        # 主要器官
        self.brain = None
        self.eyes = None
        self.mouth = None
        self.ear = None
        self.nose = None
        self.hands = None
        self.legs = None
        self.feet = None

        print(f'agent "{self.agent_id}" created by Agent_Factory.', end=self.end_char, flush=True)

    def test_init(self):
        self.test_llm = LLM_Qwen()
        # self.test_llm = LLM_Qwen(history_max_turns=3)

    # agent的初始化
    def init(self):
        self.test_init()
        return self

    # agent的所有主动行为
    def do_something(self):
        print('wrong: do_something() in Base_Agent.', end=self.end_char, flush=True)
        pass

    # agent的启动
    def life_start(self):
        print(f'agent "{self.agent_id}" ready to activate.', end=self.end_char, flush=True)

        # agent启动
        # 从线程启动 _life_cycle()
        self.thread = Thread(target=self._life_cycle)
        # self.thread = Thread(target=self._life_cycle, args=(uid,))

        self.thread.start()
        print(f'agent "{self.agent_id}" comes to life.', end=self.end_char, flush=True)
        return self

    # agent的循环
    def _life_cycle(self):
        while(True):
            # 随机行动
            if random.random() < Agent_Factory.agent_config['probability_do_something']:
                # print(f'agent "{self.agent_id}" wants to do something...', end=self.end_char, flush=True)
                self.do_something()

            # sleep
            time.sleep(Agent_Factory.agent_config['life_loop_sleep_time'])

        print(f'agent "{self.agent_id}" has reached the end of its lifecycle.', end=self.end_char, flush=True)

class Human(Base_Agent):
    def __init__(self, in_agent_id):
        super().__init__(in_agent_id)

    def do_something(self):
        print('Human, do_something():', end=self.end_char, flush=True)
        time_now =datetime.datetime.now()

        self.test_llm.ask("你现在开始提一个独特的问题，首先你要从生活、兴趣、探索、趣味、影视、游戏、男女、美食等词汇当中选中一个作为问题的方向，记住并不是向我提问，而是你对自身或世界的思考，例如：'到底什么是生活呢？'。每一次回复在形式和内容上绝对都不要重复。").sync_print()
        # self.test_llm.ask("随机推荐一本好书，简要介绍下内容和作者情况，回复形式不要很重复").sync_print()

class Animal(Base_Agent):
    def __init__(self, in_agent_id):
        super().__init__(in_agent_id)

    def do_something(self):
        print('Animal, do_something():', end=self.end_char, flush=True)

class Agent_Factory():
    # 全局配置信息
    agent_config = {
        'life_loop_sleep_time' : 0.1,           # sleep时间(second)
        'probability_do_something' : 0.001,     # 行动概率/0.1秒
        'debug_end_char' : '',                        # print的end
    }

    # 全局唯一的agent池
    _agents_pool = {
        'some_unique_agent_id':None,   # agent_id : agent_obj_ref
    }

    # 创建agent
    @classmethod
    def create_agent(cls, in_agent_id, in_agent_type='human'):
        agent = None

        # human
        if in_agent_type=='human':
            agent = Human(in_agent_id)
        # animal
        elif in_agent_type=='animal':
            agent = Animal(in_agent_id)
        # error
        else:
            return agent

        # 注册ID
        cls._agents_pool[in_agent_id] = agent

        return agent

    # 根据id获取agent引用
    @classmethod
    def get_agent(cls, in_agent_id):
        agent = cls._agents_pool.get(in_agent_id)
        return agent

def main():
    # ask_llm("如果你是大一新生，你入学第一天会做些什么？")
    Agent_Factory.agent_config['life_loop_sleep_time'] = 0.1
    Agent_Factory.agent_config['probability_do_something'] = 0.03
    Agent_Factory.agent_config['debug_end_char'] = '\n'
    human = Agent_Factory.create_agent(in_agent_id='001', in_agent_type='human')
    human.init()
    human.life_start()

    while True:
        time.sleep(1)

def main1():
    llm = LLM_Qwen()
    llm.ask('写一首诗，爱情方面的，500字。').sync_print()

    # llm = LLM_Qwen()
    # res = llm.ask("简单描述一下一个女生正在看书的情形，用英文回复。").sync_print()
    # Stable_Diffusion.quick_start('1girl, super model, showering, breasts, wet, side view, look at viewer, from below, standing, nipples, long legs, full body, sexy, beautiful', in_high_quality=True)
    # Stable_Diffusion.quick_start(res, in_high_quality=False)

def main3():
    llm = LLM_Qwen()
    while True:
        res = input('user: ')
        llm.ask(res).sync_print()

if __name__ == "__main__":
    main1()