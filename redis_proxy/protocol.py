from singleton import singleton
from enum import Enum, unique
from dataclasses import dataclass, asdict, field

@unique
class Redis_Task_Type(Enum):
    LLM = 'LLM'
    T2I = 'T2I'
    TTS = 'TTS'

@unique
class Redis_LLM_Command(Enum):
    INIT = 'INIT'
    # START = 'START'
    CANCEL = 'CANCEL'
    ASK = 'ASK'