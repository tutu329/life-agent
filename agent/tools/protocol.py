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

# ---------------------------------pydantic导出示例---------------------------------
# class M(BaseModel):
#     # 必填：必须出现
#     a: int
#
#     # 必填但可为 None：必须出现，但能是 null
#     b: Optional[int]  # 或 int | None
#
#     # ---------可省略：不出现也行；出现时可为 None--------，后续用m.model_dump(exclude_unset=True)即可
#     c: Optional[int] = None
#
#     # 可省略：不出现也行；出现时必须是 int
#     d: int | None = Field(default=None)  # 出现且为 None 也允许

# m = M(a=1, b=None)  # c、d 未提供
# m.model_dump(exclude_unset=True)
# # -> 只包含 a、b
#
# m.model_dump(exclude_none=True)
# # -> 过滤掉 None 值的字段（此时 b 会被去掉）
#
# m.model_dump(exclude_unset=True, exclude_none=True)
# # -> 只留 a（因为 b 是 None 被过滤，c/d 未提供被过滤）
# --------------------------------/pydantic导出示例---------------------------------