from abc import ABC, abstractmethod

class legacy_Web_Server_Base(ABC):
    def __init__(self):
        super().__init__()
        print('-------------Web_Server_Base.__init__()-----------------')

    @abstractmethod
    def init(self):
        pass

    @abstractmethod
    def run(self):
        pass

    # 设置输出stream的buf
    @abstractmethod
    def set_stream(
            self,
            result_output_func,
            thinking_output_func,
            log_output_func,
            tool_result_data_output_func
    ):
        pass