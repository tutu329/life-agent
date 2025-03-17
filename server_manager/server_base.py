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

    @abstractmethod
    def set_output_stream_buf(self, in_output_stream_buf):
        pass