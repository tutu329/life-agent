from abc import ABC, abstractmethod

class Server_Base(ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def init(self):
        pass

    @abstractmethod
    def run(self):
        pass

    # 最终输出的buf
    @abstractmethod
    def set_stream_result(self, result_output_func):
        pass

    # thinking输出的buf
    @abstractmethod
    def set_stream_thinking(self, thinking_output_func):
        pass

    # log输出的buf
    @abstractmethod
    def set_stream_log(self, log_output_func):
        pass

    # tool client data输出的buf
    @abstractmethod
    def set_stream_tool_result_data(self, tool_result_data_output_func):
        pass