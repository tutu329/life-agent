from typing import Any, Dict, List, Literal, Optional, Union, Tuple, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict

class Uno_Command(BaseModel):
    # 主要变量
    # uno_text
    # uno_
    # uno_
    # uno_
    # uno_
    uno_insert_text_and_return      :Dict[str, Any] = "{{'MessageId': 'Send_UNO_Command', 'Values': {{'Command': '.uno:InsertText', 'Args': {{'Text': {{'type': 'string', 'value': '{uno_text}'}}}}}}}}"
