from agent.agent_web_client.protocol import FastAPI_Remote_Tool_Base, FastFPI_Remote_Tool_Register_Data
from agent.tools.protocol import Action_Result


class Remote_Folder_Tool(FastAPI_Remote_Tool_Base):
    def __init__(self, register_data:FastFPI_Remote_Tool_Register_Data):
        super().__init__(self, register_data)

    def tool_func(self, request:dict) -> Action_Result:
        print('helloworld')

