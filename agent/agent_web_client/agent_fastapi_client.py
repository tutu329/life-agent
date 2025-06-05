import httpx
from sseclient import SSEClient  # pip install sseclient-py

from agent.tools.protocol import Registered_Remote_Tool_Data
from agent.tools.protocol import Tool_Call_Paras
from agent.tools.remote_tool_class import generate_tool_class_dynamically
from agent.core.agent_config import Agent_Config

def agent_fastapi_client():
    pass

def main_test_2_level_agents_system():
    def test_agent_sync():
        """Python测试Agent服务器"""
        # url = "http://localhost:5120/run_agent_sync"
        url = "http://powerai.cc:5120/run_agent_sync"

        # 测试数据
        data = {
            # "query": '请告诉我当前文件夹下有哪些文件',
            "query": '请告诉我"agent"下有哪些文件',
            # "query": '请告诉我"./"下有哪些文件',
            # "query": '请告诉我"file_to_find.txt"在"d:\\demo\\"文件夹的哪个具体文件夹中',
            "base_url": 'https://api.deepseek.com/v1',
            "api_key": 'sk-c1d34a4f21e3413487bb4b2806f6c4b8',
            "model_id": 'deepseek-chat'
        }

        try:
            print("🚀 发送请求到Agent服务器...")
            response = requests.post(url, json=data)

            if response.status_code == 200:
                result = response.json()
                print("✅ 请求成功!")
                print("📄 响应内容:")
                print(result)
                # print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"❌ 请求失败: {response.status_code}")
                print(response.text)

        except requests.exceptions.ConnectionError:
            print("❌ 连接失败！请确保agent_server.py已启动")
        except Exception as e:
            print(f"❌ 发生错误: {e}")

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