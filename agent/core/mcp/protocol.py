from typing import List, Dict, Any, Type, Literal, Optional, Callable
from pydantic import BaseModel, Field, ConfigDict

class MCP_Server_Request(BaseModel):
    url                 :str
    allowed_tool_names  :List[str] = Field(default_factory=list)