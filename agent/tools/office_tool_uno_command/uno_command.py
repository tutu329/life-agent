from typing import Any, Dict, List, Literal, Optional, Union, Tuple, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict

Uno_Color: Dict[str, str] = {
    "red":    "16711680",   # 0xFF0000
    "green":  "65280",      # 0x00FF00
    "blue":   "255",        # 0x0000FF
    "black":  "0",          # 0x000000
    "white":  "16777215",   # 0xFFFFFF
    "gray":   "8421504",    # 0x808080 (中灰)
    "yellow": "16776960",   # 0xFFFF00
}


class Uno_Command(BaseModel):
    # 主要输入变量
    # uno_text
    # uno_char_back_color
    # uno_char_size
    # uno_font
    # uno_char_color
    # uno_outline
    # uno_outline_level

    # 插入文本
    uno_insert_text                 :Dict[str, Any] = "{{'MessageId': 'Send_UNO_Command', 'Values': {{'Command': '.uno:InsertText', 'Args': {{'Text': {{'type': 'string', 'value': '{uno_text}'}}}}}}}}"
    # 插入文本并换行
    uno_insert_text_and_return      :Dict[str, Any] = "{{'MessageId': 'Send_UNO_Command', 'Values': {{'Command': '.uno:InsertText', 'Args': {{'Text': {{'type': 'string', 'value': '{uno_text}\\n'}}}}}}}}"

    # 文字的缩进级别（不是大纲级别）
    uno_set_outline                 :Dict[str, Any] = "{{'MessageId': 'Send_UNO_Command', 'Values': {{'Command': '.uno:SetOutline', 'Args': {{'SetOutline': {{'type': 'long', 'value': '{uno_outline}'}}}}}}}}"

    # 文字的大纲级别(测试无效，long、short都不行)
    uno_outline_level               :Dict[str, Any] = "{{'MessageId': 'Send_UNO_Command', 'Values': {{'Command': '.uno:OutlineLevel', 'Args': {{'OutlineLevel': {{'type': 'short', 'value': '{uno_outline_level}'}}}}}}}}"

    # 文字字体
    uno_font                        :Dict[str, Any] = "{{'MessageId': 'Send_UNO_Command', 'Values': {{'Command': '.uno:CharFontName','Args':{{'CharFontName.FamilyName':{{'type':'string','value': '{uno_font}'}}}}}}}}"
    # 文字粗体
    uno_bold                        :Dict[str, Any] = "{'MessageId': 'Send_UNO_Command', 'Values': {'Command': '.uno:Bold'}}"

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
