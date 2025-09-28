from typing import List, Dict, Any, Type, Literal, Optional, Callable
from pydantic import BaseModel, Field, ConfigDict

# --------------------------------tool参数示例---------------------------------
# {
#     "type": "function",
#     "name": "add_tool",
#     "description": "计算两个数的和",
#     "strict": True,  # 让模型严格遵循 JSON Schema
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "a": {"type": "number", "description": "a"},
#             "b": {"type": "number", "description": "b"},
#         },
#         "required": [],
#         "additionalProperties": False,
#     },
# },
# -------------------------------/tool参数示例---------------------------------

Property_Type = Literal["integer", "number", "boolean", "string"]

class Tool_Property(BaseModel):
    type            :Property_Type              # 如"integer", "number", "boolean", "string"
    description     :str                        # 如"加数"、"被加数"
    enum            :Optional[List[str]] = None # 如属性unit的可选值：["c", "f"]

class Tool_Parameters(BaseModel):
    type            :str = 'object'
    properties      :Dict[str, Tool_Property]          # 如{ 'a': {}, 'b': {} }
    required        :List[str] = Field(default_factory=list)    # 如['a', 'b']
    additionalProperties :bool = False

class Tool_Request(BaseModel):
    type            :str = 'function'
    name            :str    # 如'add_tool'
    description     :str    # 如'计算两个数的和'
    strict          :bool = True
    parameters      :Tool_Parameters

    # 所调用的函数
    # 仅在本地使用，不参与 JSON 序列化
    func        : Optional[Callable] = Field(default=None, exclude=True, repr=False)

    # 允许 pydantic 接受 Callable 等任意类型（否则有些版本会抱怨）
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')