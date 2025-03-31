from abc import ABC, abstractmethod
import uuid

class Mem_Base(ABC):
    def __init__(self):
        super().__init__()
        self.id = 'mem_' + str(uuid.uuid4())

    @abstractmethod
    def init(self):
        pass