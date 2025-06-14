import requests
import httpx
from sseclient import SSEClient  # pip install sseclient-py
import threading
import time

from agent.tools.protocol import Registered_Remote_Tool_Data
from agent.tools.protocol import Tool_Call_Paras
from agent.tools.generate_tool_class_dynamically import generate_tool_class_dynamically
from agent.core.agent_config import Agent_Config, Agent_As_Tool_Config
from agent.agent_web_server.agent_fastapi_server import Agents_System_Request, Query_Agent_Request, Agent_Status_Request

from config import Port
from config import dblue, dyellow, dgreen, dcyan, dred

def agent_fastapi_client():
    pass


def _listen_to_stream(base_url: str, stream_id: str, stream_name: str):
    """监听单个 SSE 流"""
    # 注意：这里需要构建正确的流URL
    # 假设你的服务器基础URL是 http://powerai.cc:5120
    server_base = base_url.replace('/api/query_2_level_agents_system', '')
    stream_url = f"{server_base}/api/query_2_level_agents_system/stream/{stream_id}/{stream_name}"
    print(f"🔗 连接到流: {stream_name} - {stream_url}")

    try:
        response = requests.get(stream_url, stream=True)
        if response.status_code != 200:
            print(f"❌ 流连接失败: {response.status_code} - {response.text}")
            return

        client = SSEClient(response)

        if stream_name=='output':
            o = dgreen
        elif stream_name=='thinking':
            o = dblue
        elif stream_name=='final_answer':
            o = dred
        elif stream_name=='log':
            o = print
        elif stream_name == 'tool_rtn_data':
            o = dyellow

        o(f'[{stream_name}]', end='')
        for event in client.events():
            o(f"{event.data}", end='')
        o()
    except Exception as e:
        print(f"❌ 流 {stream_name} 出错: {e}")


def main_test_2_level_agents_system():
    """Python测试Agent服务器 - 方案1调用方式"""
    # 第一步：启动任务
    start_url = "https://localhost:5110/api/start_2_level_agents_stream"
    # start_url = "http://powerai.cc:5120/api/start_2_level_agents_stream"

    # request = {
    #     "query": '请告诉我"./"下有哪些文件',
    #     'agent_config':Agent_Config(
    #         base_url='https://api.deepseek.com/v1',
    #         api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
    #         # llm_model_id='deepseek-reasoner',    # 模型指向 DeepSeek-R1-0528
    #         llm_model_id='deepseek-chat',        # 模型指向 DeepSeek-V3-0324
    #     ).dict(),
    # }

    # request = {
    #     "query": '请告诉我"./"下有哪些文件',
    #     'agent_config':Agent_Config(
    #         base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
    #         api_key='sk-9f507c06d7534acf978cf30091bc5529',  # 通义千问官网
    #         llm_model_id='qwen3-235b-a22b',  # 模型指向 qwen3-235b-a22b
    #     ).dict(),
    # }
    request = Agents_System_Request(
        query=r'我叫电力用户，请告诉./文件夹下有哪些文件',
        remote_tools=[
            Registered_Remote_Tool_Data(
                name="Remote_Folder_Tool",
                description="返回远程服务器上指定文件夹下所有文件和文件夹的名字信息。",
                parameters=[
                    {
                        "name": "dir",
                        "type": "string",
                        "description": "本参数为文件夹所在的路径",
                        "required": "True",
                    }
                ],
                endpoint_url=f"https://localhost:{Port.remote_tool_fastapi_server}/Folder_Tool",
                method="POST",
                timeout=15,
            )
        ],
        upper_agent_config=Agent_Config(
            tool_names=['Human_Console_Tool'],
            exp_json_path='my_2_levels_mas_exp.json',

            base_url='https://api.deepseek.com/v1',
            api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
            # llm_model_id='deepseek-reasoner',  # 模型指向 DeepSeek-R1-0528
            llm_model_id='deepseek-chat',  # 模型指向 DeepSeek-V3-0324
            temperature=0.65
        ),
        lower_agents_config=[
            Agent_As_Tool_Config(
                tool_names=['Human_Console_Tool', 'Remote_Folder_Tool'],
                exp_json_path='',
                as_tool_name='Folder_Agent_As_Tool',
                as_tool_description='本工具用于获取文件夹中的文件和文件夹信息',

                base_url='https://api.deepseek.com/v1',
                api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
                # llm_model_id = 'deepseek-reasoner',  # 模型指向 DeepSeek-R1-0528
                llm_model_id='deepseek-chat',  # 模型指向 DeepSeek-V3-0324
                temperature=0.70
            )
        ]
    )

    try:
        print("🚀 第一步：发送请求启动Agent任务...")
        response = requests.post(start_url, json=request.dict())

        if response.status_code == 200:
            result = response.json()
            print("✅ 任务启动成功!")
            print("📄 启动响应:")
            print(result)

            # 获取 stream_id 和可用流
            stream_id = result.get('id')
            available_streams = result.get('streams', [])

            if stream_id and available_streams:
                print(f"\n🆔 获得流 ID: {stream_id}")
                print(f"📡 可用流列表: {available_streams}")

                print(f"\n🔄 第二步：开始监听 SSE 流...")

                # 为每个流创建线程来监听
                threads = []
                for stream_name in available_streams:
                    thread = threading.Thread(
                        target=_listen_to_stream,
                        args=(start_url, stream_id, stream_name)
                    )
                    thread.daemon = True
                    thread.start()
                    threads.append(thread)

                # 等待所有流完成（或手动中断）
                try:
                    print("⏳ 监听流中... (按 Ctrl+C 停止)")
                    for thread in threads:
                        thread.join()
                except KeyboardInterrupt:
                    print("\n⚠️ 用户中断，停止监听流")
            else:
                print("❌ 没有获得有效的流ID或可用流列表")

        else:
            print(f"❌ 任务启动失败: {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("❌ 连接失败！请确保agent_fastapi_server.py已启动")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

# def main_test_2_level_agents_system_without_remote_tool():
#     start_url = "http://localhost:5110/api/start_2_level_agents_stream"
#
#     request = Agents_System_Request(
#         query=r'我叫电力用户，请告诉./文件夹下有哪些文件',
#         remote_tools=[],
#         upper_agent_config=Agent_Config(
#             tool_names=['Human_Console_Tool'],
#             exp_json_path='my_2_levels_mas_exp.json',
#
#             base_url='https://api.deepseek.com/v1',
#             api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
#             # llm_model_id='deepseek-reasoner',  # 模型指向 DeepSeek-R1-0528
#             llm_model_id='deepseek-chat',  # 模型指向 DeepSeek-V3-0324
#             temperature=0.65
#         ),
#         lower_agents_config=[
#             Agent_As_Tool_Config(
#                 tool_names=['Human_Console_Tool', 'Folder_Tool'],
#                 exp_json_path='',
#                 as_tool_name='Folder_Agent_As_Tool',
#                 as_tool_description='本工具用于获取文件夹中的文件和文件夹信息',
#
#                 base_url='https://api.deepseek.com/v1',
#                 api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
#                 # llm_model_id = 'deepseek-reasoner',  # 模型指向 DeepSeek-R1-0528
#                 llm_model_id='deepseek-chat',  # 模型指向 DeepSeek-V3-0324
#                 temperature=0.70
#             )
#         ]
#     )
#
#     try:
#         print("🚀 第一步：发送请求启动Agent任务...")
#         response = requests.post(start_url, json=request.dict())
#
#         if response.status_code == 200:
#             result = response.json()
#             print("✅ 任务启动成功!")
#             print("📄 启动响应:")
#             print(result)
#
#             # 获取 stream_id 和可用流
#             stream_id = result.get('id')
#             available_streams = result.get('streams', [])
#
#             if stream_id and available_streams:
#                 print(f"\n🆔 获得流 ID: {stream_id}")
#                 print(f"📡 可用流列表: {available_streams}")
#
#                 print(f"\n🔄 第二步：开始监听 SSE 流...")
#
#                 # 为每个流创建线程来监听
#                 threads = []
#                 for stream_name in available_streams:
#                     thread = threading.Thread(
#                         target=_listen_to_stream,
#                         args=(start_url, stream_id, stream_name)
#                     )
#                     thread.daemon = True
#                     thread.start()
#                     threads.append(thread)
#
#                 # 等待所有流完成（或手动中断）
#                 try:
#                     print("⏳ 监听流中... (按 Ctrl+C 停止)")
#                     for thread in threads:
#                         thread.join()
#                 except KeyboardInterrupt:
#                     print("\n⚠️ 用户中断，停止监听流")
#             else:
#                 print("❌ 没有获得有效的流ID或可用流列表")
#
#         else:
#             print(f"❌ 任务启动失败: {response.status_code}")
#             print(response.text)
#
#     except requests.exceptions.ConnectionError:
#         print("❌ 连接失败！请确保agent_server.py已启动")
#     except Exception as e:
#         print(f"❌ 发生错误: {e}")

def main_test_2_level_agents_system_without_remote_tool():
    server_name = 'powerai.cc'
    # server_name = 'localhost'

    request = Agents_System_Request(
        remote_tools=[],
        upper_agent_config=Agent_Config(
            tool_names=['Human_Console_Tool'],
            exp_json_path='my_2_levels_mas_exp.json',

            base_url='https://api.deepseek.com/v1',
            api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
            # llm_model_id='deepseek-reasoner',  # 模型指向 DeepSeek-R1-0528
            llm_model_id='deepseek-chat',  # 模型指向 DeepSeek-V3-0324
            temperature=0.65
        ),
        lower_agents_config=[
            Agent_As_Tool_Config(
                tool_names=['Human_Console_Tool', 'Folder_Tool'],
                exp_json_path='',
                as_tool_name='Folder_Agent_As_Tool',
                as_tool_description='本工具用于获取文件夹中的文件和文件夹信息',

                base_url='https://api.deepseek.com/v1',
                api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
                # llm_model_id = 'deepseek-reasoner',  # 模型指向 DeepSeek-R1-0528
                llm_model_id='deepseek-chat',  # 模型指向 DeepSeek-V3-0324
                temperature=0.70
            )
        ]
    )

    try:
        start_url = f"https://{server_name}:5110/api/start_2_level_agents_system"
        print("🚀 第一步：发送请求启动Agents System...")
        response = requests.post(start_url, json=request.dict())

        if response.status_code == 200:
            result = response.json()
            print("✅ Agents System已启动!")
            print(f"✅ result: '{result}'")
        else:
            print(f"❌ Agents System启动失败: {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("❌ 连接失败！请确保agent_fastapi_server.py已启动")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

    query = r'我叫电力用户，请告诉./文件夹下有哪些文件'
    agent_id = result   # result即为agent_id
    request = Query_Agent_Request(
        agent_id=agent_id,    # result即为agent_id
        query=query
    )

    try:
        start_url = f"https://{server_name}:5110/api/query_2_level_agents_system"
        print("🚀 第二步：对Agents System进行query...")
        print(f"🚀 query内容: '{query}'")
        response = requests.post(start_url, json=request.dict())

        if response.status_code == 200:
            result = response.json()
            print("✅ 对Agents System的query任务启动成功!")
            print("📄 启动响应:")
            print(result)

            # 获取 stream_id 和可用流
            stream_id = result.get('id')
            available_streams = result.get('streams', [])

            if stream_id and available_streams:
                print(f"\n🆔 获得流 ID: {stream_id}")
                print(f"📡 可用流列表: {available_streams}")

                print(f"\n🔄 第二步：开始监听 SSE 流...")

                # 为每个流创建线程来监听
                threads = []
                for stream_name in available_streams:
                    thread = threading.Thread(
                        target=_listen_to_stream,
                        args=(start_url, stream_id, stream_name)
                    )
                    thread.daemon = True
                    thread.start()
                    threads.append(thread)

                # 等待所有流完成（或手动中断）
                try:
                    print("⏳ 监听流中... (按 Ctrl+C 停止)")
                    # for thread in threads:
                    #     thread.join()
                except KeyboardInterrupt:
                    print("\n⚠️ 用户中断，停止监听流")
            else:
                print("❌ 没有获得有效的流ID或可用流列表")

        else:
            print(f"❌ 任务启动失败: {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("❌ 连接失败！请确保agent_fastapi_server.py已启动")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

    start_url = f"https://{server_name}:5110/api/get_agent_status"
    print("检查对Agents System的query是否完成...")
    request = Agent_Status_Request(
        agent_id=agent_id
    )
    while(True):
        response = requests.post(start_url, json=request.dict())
        time.sleep(0.5)
        if response.status_code == 200:
            status = response.json()
            # print(f'status: "{status}"')

            if status['finished']==True:
                break
        time.sleep(1)
    print(f'agent任务执行已完成，客户端退出！')


def main_test_2_level_agents_system_simple():
    """简化版本：只监听一个流"""
    # 第一步：启动任务
    start_url = "https://powerai.cc:5120/api/start_2_level_agents_stream"
    data = {
        "query": '请告诉我"./"下有哪些文件',
        "base_url": 'https://api.deepseek.com/v1',
        "api_key": 'sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        "llm_model_id": 'deepseek-chat'
    }

    try:
        # 启动任务
        print("🚀 启动任务...")
        response = requests.post(start_url, json=data)

        if response.status_code == 200:
            result = response.json()
            stream_id = result.get('id')
            available_streams = result.get('streams', [])

            if stream_id and available_streams:
                # 监听第一个可用流
                stream_name = available_streams[0]
                server_base = start_url.replace('/api/start_2_level_agents_stream', '')
                stream_url = f"{server_base}/api/start_2_level_agents_stream/stream/{stream_id}/{stream_name}"

                print(f"🔗 监听流: {stream_url}")

                # 直接在主线程监听
                stream_response = requests.get(stream_url, stream=True)
                if stream_response.status_code == 200:
                    client = SSEClient(stream_response)
                    for event in client.events():
                        print(f"📨 {event.data}")
                else:
                    print(f"❌ 流连接失败: {stream_response.status_code}")
        else:
            print(f"❌ 启动失败: {response.status_code}")

    except Exception as e:
        print(f"❌ 错误: {e}")

# server端简单测试fastapi的remote_tool是否正常
def main_test_remote_tool_fastapi_server_launched_by_client():
    # -------------------第一步：将fastapi发布的remote_tool注册到server的tool_manager里---------------------------
    para = Registered_Remote_Tool_Data(
        name="Remote_Folder_Tool",
        description="返回远程服务器上指定文件夹下所有文件和文件夹的名字信息。",
        parameters=[{"name": "dir", "type": "string"}],
        endpoint_url="https://localhost:5120/Folder_Tool",   # 'Folder_Tool'大小写必须正确
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
    # main_test_remote_tool_fastapi_server_launched_by_client()
    # main_test_2_level_agents_system()
    main_test_2_level_agents_system_without_remote_tool()
