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
    def set_output_stream_buf(self, in_output_stream_buf):
        pass

    # thinking输出的buf
    @abstractmethod
    def set_thinking_stream_buf(self, in_thinking_stream_buf):
        pass

    # log输出的buf
    @abstractmethod
    def set_log_stream_buf(self, in_log_stream_buf):
        pass

    # tool client data输出的buf
    @abstractmethod
    def set_tool_client_data_stream_buf(self, in_tool_client_data_stream_buf):
        pass