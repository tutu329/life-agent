import time, random
from threading import Thread

from tools.llm.api_client import LLM_Client
from agent.async_environment import *



# =============================== LLM接口 =================================
# def ask_llm_with_history(user_input, his=[]):
#     return ask(user_input=user_input, his=his)

class Agent_Memory():
    def __int__(self):
        pass

    def load(self):
        pass

    def save(self):
        pass

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
        self.memory:Agent_Memory = None
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

    def test_init(self, action_question, role_prompt, example_prompts=None, nagetive_example_prompt='', style_prompt='', other_requirement=''):
        self.test_env=None
        self.test_action_question = action_question

        self.test_llm = LLM_Client(url='https://powerai.cc:8001/v1')
        # self.test_llm = LLM_Client(url='http://192.168.124.33:8001/v1')
        # role_prompt = '你是一位书籍收藏爱好者，对于国内外各领域经典著作了如指掌。'
        if example_prompts is None:
            example_prompts = [
                # '例如，user发送给你的文字中有单个字的笔误："你是我的好彭友，我们明天粗去玩吧？"，你要指出"彭"应为"朋"、"粗"应为"出"。',
                # '例如，user发送给你的文字中有涉及语义的笔误："我们已对全社会效益已经财务效益进行了全面分析。"，你要指出"已经"应为"以及"。',
            ]
        # nagetive_example_prompt = '需要注意的是，一个词语不完整或者多余，并不属于错别字，例如"社会效益最大"应为"社会效益最大化"、"电影院"应为"电影"就不属于错别字，不要将这种情况误判为错别字。'
        # style_prompt = '你的错别字修改意见要以json格式返回，具体的json格式要求是，有错别字时像这样：{"result":"有错别字", [{"原有词语":"彭友", "修改意见":"朋友"}, {"原有词语":"粗去", "修改意见":"出去"}]}，没用错别字时像这样：{"result":"无错别字"}。'
        # other_requirement = '直接返回json意见，不作任何解释。一步一步想清楚。'
        self.test_llm.set_role_prompt(role_prompt + ''.join(example_prompts) + nagetive_example_prompt + style_prompt + other_requirement)

    # agent的初始化
    def init(self):
        return self

    def observe(self):
        pass

    def think(self):
        pass

    def action(self):
        pass

    # agent的所有主动行为
    def do_something(self):
        print('ERROR: do_something() invoked in Base_Agent.', end=self.end_char, flush=True)
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

    def observe(self):
        print(f'[{self.agent_id}:observe]:')
        pass

    def think(self):
        print(f'[{self.agent_id}:think]:')
        pass

    def action(self):
        print(f'[{self.agent_id}:action]:')
        pass

    def do_something(self):
        print(f'[{self.agent_id}:do_something]:', end=self.end_char, flush=True)

        self.observe()
        self.think()
        self.action()

        # time_now =datetime.now()

        res = self.test_llm.ask_prepare(self.test_action_question).get_answer_and_sync_print()
        self.test_env = Async_Environment()
        self.test_env.append_event(
            Event_Type.TEXT,
            self.agent_id,
            'ALL',
            Action_Type.SPEAK,
            Action_Tool.NONE,
            res
        )
        self.test_env.print_history()

        # self.test_llm.ask_prepare("在1400年-2000年当中随机选择一个年代，如1500-1600年、1900-2000年等等都行，并推荐一本出版于这个年代的畅销书，不要重复。只回复书名、作者、出版时间和书中主人公。").get_answer_and_sync_print()
        # self.test_llm.pr
        # self.test_llm.ask_prepare("你现在开始提一个独特的问题，首先你要从生活、兴趣、探索、趣味、影视、游戏、男女、美食等词汇当中选中一个作为问题的方向，记住并不是向我提问，而是你对自身或世界的思考，例如：'到底什么是生活呢？'。每一次回复在形式和内容上绝对都不要重复。").get_answer_and_sync_print()
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
        'probability_do_something' : 0.0001,     # 行动概率/0.1秒
        'debug_end_char' : '',                  # print中的end参数，用于适应stream输出，console下面应为''
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
    Agent_Factory.agent_config['probability_do_something'] = 0.5
    Agent_Factory.agent_config['debug_end_char'] = '\n'
    human = Agent_Factory.create_agent(in_agent_id='笨笨', in_agent_type='human')
    human.test_init(
        "在1400年-2000年当中随机选择一个年代，如1500-1600年、1900-2000年等等都行，并推荐一本出版于这个年代的畅销书，不要重复。只回复书名、作者、出版时间和书中主人公。",
        '你是一位书籍收藏爱好者，对于国内外各领域经典著作了如指掌。'
    )
    human.life_start()

    while True:
        time.sleep(1)

def main_gr():
    import gradio as gr

    with gr.Blocks() as ui:
        user_input = gr.Textbox(
            # lines=3,
            max_lines=20,
            autofocus=True,
            scale=16,
            show_label=False,
            placeholder="输入文本并按回车，或者上传文件",
            container=False,
        )

    # demo.launch()
    # demo.launch(server_name='localhost', server_port=6000)
    # demo.launch(server_name='0.0.0.0', server_port=6000)
    ui.queue().launch()
    # ui.queue().launch(server_name='0.0.0.0', server_port=2222)

if __name__ == "__main__":
    main()
    # main_gr()