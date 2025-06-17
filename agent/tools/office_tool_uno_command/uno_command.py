from typing import Any, Dict, List, Literal, Optional, Union, Tuple, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict

Uno_Color:Dict[str, str] = {
    'red'           :"16776960",
    'green'         :"16776960",
    'blue'          :"16776960",
    'black'         :"16776960",
    'white'         :"16776960",
    'gray'          :"16776960",
    'yellow'        :"16776960",
}

class Uno_Command(BaseModel):
    # 主要输入变量
    # uno_text
    # uno_char_back_color
    # uno_char_size
    # uno_font
    # uno_char_color

    # 插入文本
    uno_insert_text                 :Dict[str, Any] = "{{'MessageId': 'Send_UNO_Command', 'Values': {{'Command': '.uno:InsertText', 'Args': {{'Text': {{'type': 'string', 'value': '{uno_text}'}}}}}}}}"
    # 插入文本并换行
    uno_insert_text_and_return      :Dict[str, Any] = "{{'MessageId': 'Send_UNO_Command', 'Values': {{'Command': '.uno:InsertText', 'Args': {{'Text': {{'type': 'string', 'value': '{uno_text}\\n'}}}}}}}}"

    # 文字字体
    uno_font                        :Dict[str, Any] = "{{'MessageId': 'Send_UNO_Command', 'Values': {{'Command': '.uno:CharFontName','Args':{{'CharFontName.FamilyName':{{'type':'string','value': '{uno_font}'}}}}}}}}"
    # 文字粗体
    uno_bold                        :Dict[str, Any] = "{'MessageId': 'Send_UNO_Command', 'Values': {'Command': '.uno:Bold'}"

    # 文字颜色
    uno_char_color                  :Dict[str, Any] = "{{'MessageId':'Send_UNO_Command','Values':{{'Command':'.uno:Color','Args':{{'Color':{{'type':'long','value': '{uno_char_color}'}}}}}}}}"

    # 文字背景色
    uno_char_back_color             :Dict[str, Any] = "{{'MessageId':'Send_UNO_Command','Values':{{'Command':'.uno:CharBackColor','Args':{{'CharBackColor':{{'type':'long','value': '{uno_char_back_color}'}}}}}}}}"

    # 文字大小
    uno_char_size                   :Dict[str, Any] = "{{'MessageId': 'Send_UNO_Command', 'Values': {{'Command': '.uno:FontHeight','Args':{{'FontHeight.Height':{{'type':'short','value': '{uno_char_size}'}}, 'FontHeight.Prop':{{'type':'short','value': '100'}}}}}}}}"

    # 文字上标
    uno_char_super_script           :Dict[str, Any] = "{'MessageId':'Send_UNO_Command','Values':{'Command':'.uno:SuperScript'}}"

    # 文字下标
    uno_char_sub_script             :Dict[str, Any] = "{'MessageId':'Send_UNO_Command','Values':{'Command':'.uno:SubScript'}}"

    # 段落居中
    uno_center                      :Dict[str, Any] = "{'MessageId':'Send_UNO_Command','Values':{'Command':'.uno:CenterPara'}}"
    # 段落不居中
    uno_uncenter                    :Dict[str, Any] = "{'MessageId':'Send_UNO_Command','Values':{'Command':'.uno:LeftPara'}}"
