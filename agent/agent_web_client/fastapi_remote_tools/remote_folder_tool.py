from agent.agent_web_client.protocol import FastAPI_Remote_Tool_Base, FastFPI_Remote_Tool_Register_Data
from agent.tools.legacy_protocol import Action_Result

from agent.tools.folder_tool import Folder_Tool

class Remote_Folder_Tool_Example(FastAPI_Remote_Tool_Base):
    """
    Remote_Folder_Tool_Example类，示例了如何将Base_Tool的子类转化为fastapi接口
    Base_Tool的子类，通过register_data.tool_class传给FastAPI_Remote_Tool_Base，从而能访问其call()
    """
    def __init__(self):
        register_data = FastFPI_Remote_Tool_Register_Data(
            tool=Folder_Tool()    # 本example工具直接与Folder_Tool关联
        )
        super().__init__(register_data)