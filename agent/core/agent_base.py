from abc import ABC, abstractmethod
from uuid import uuid4

from agent.core.agent_config import Agent_Config
from config import dblue

class Agent_Base(ABC):
    def __init__(self, agent_config:Agent_Config):
        # 1、agent_id
        self.agent_id = str(uuid4())

        # 2、top_agent_id
        # 顶层的agent_id，主要用于多层agents系统中，让top_agent_id<-->connection，而与下层agent_id无关
        # top_agent_id的形成有2种情况：
        # 1）多层agents system中，靠parent agent注入
        # 2）自己即为top agent，则self.top_agent_id=self.agent_id
        if agent_config.top_agent_id:
        # 外部注入了top_agent_id
            self.top_agent_id = agent_config.top_agent_id
        else:
            # 外部没有注入top_agent_id
            self.top_agent_id = self.agent_id

        # 3、name(或者初始化提供，或者基于agent_id)
        if agent_config.agent_name:
            self.name = agent_config.agent_name
        else:
            self.name = 'agent_' + self.agent_id

        self.agent_config = agent_config
        self._init_print()

    def _init_print(self):
        dblue(self.agent_config)

    @abstractmethod
    def init(self):
        pass

    @abstractmethod
    def run(self):
        pass

    # 设置输出stream的buf
    # @abstractmethod
    # def set_stream(
    #         self,
    #         result_output_func,
    #         thinking_output_func,
    #         log_output_func,
    #         tool_result_data_output_func
    # ):
    #     pass