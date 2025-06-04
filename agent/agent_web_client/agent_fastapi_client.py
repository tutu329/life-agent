from agent.tools.protocol import Registered_Remote_Tool_Data
from agent.tools.protocol import Tool_Call_Paras
from agent.tools.remote_tool_class import generate_tool_class_dynamically
from agent.core.agent_config import Agent_Config

def agent_fastapi_client():
    pass

# server端简单测试fastapi的remote_tool是否正常
def main_test_remote_tool_fastapi_server_launched_by_client():
    # -------------------第一步：将fastapi发布的remote_tool注册到server的tool_manager里---------------------------
    para = Registered_Remote_Tool_Data(
        name="Remote_Folder_Tool",
        description="返回远程服务器上指定文件夹下所有文件和文件夹的名字信息。",
        parameters=[{"name": "dir", "type": "string"}],
        endpoint_url="http://localhost:5120/Folder_Tool",   # 'Folder_Tool'大小写必须正确
        method="POST",
        timeout=15,
    )
    # 将fastapi的调用转为tool_class的call()
    Remote_Folder_Tool = generate_tool_class_dynamically(para)
    # ------------------/第一步：将fastapi发布的remote_tool注册到server的tool_manager里---------------------------

    # ----------------------------------第二步：调用remote_tool的call()-----------------------------------------
    tool_call_paras = Tool_Call_Paras(
        callback_tool_paras_dict={"dir": "./"},     # 'dir'必需与Folder_Tool的parameters一致
        callback_agent_config=Agent_Config(),
        callback_agent_id='xxxxxxxx',
        callback_last_tool_ctx=None,
        callback_father_agent_exp='',
    )
    result = Remote_Folder_Tool().call(tool_call_paras)
    print(f"远端返回：{result!r}")
    # ---------------------------------/第二步：调用remote_tool的call()-----------------------------------------

# ============= 示范用法 =============
if __name__ == "__main__":
    main_test_remote_tool_fastapi_server_launched_by_client()