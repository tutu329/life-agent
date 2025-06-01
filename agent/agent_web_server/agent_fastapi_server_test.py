import requests
import json
import sseclient  # 需要安装: pip install sseclient-py
import threading
import time


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


def test_agent_stream():
    """测试Agent流式调用"""
    print("\n🌊 测试流式调用...")
    url = "http://powerai.cc:5120/run_agent"

    data = {
        "query": '请告诉我"./"下有哪些文件',
        # "query": '请告诉我"file_to_find.txt"在"d:\\demo\\"文件夹的哪个具体文件夹中',
        "base_url": "http://powerai.cc:28001/v1",
        "api_key": "empty",
        "enable_stream": True
    }

    try:
        # 1. 启动Agent（获取session_id和stream_url）
        print("🚀 启动Agent...")
        response = requests.post(url, json=data)

        if response.status_code != 200:
            print(f"❌ 启动失败: {response.status_code}")
            print(response.text)
            return

        result = response.json()
        print("✅ Agent启动成功!")
        print("📄 启动响应:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 2. 连接SSE流
        session_id = result.get("session_id")
        if not session_id:
            print("❌ 未获取到session_id")
            return

        stream_url = f"http://powerai.cc:5120/stream/{session_id}"
        print(f"\n📡 连接SSE流: {stream_url}")

        # 3. 接收流式数据
        sse_response = requests.get(stream_url, stream=True)
        client = sseclient.SSEClient(sse_response)

        print("🎯 开始接收流式数据:")
        print("-" * 50)

        for event in client.events():
            if event.data:
                try:
                    data = json.loads(event.data)
                    event_type = data.get("type", "unknown")
                    content = data.get("content", "")
                    timestamp = data.get("timestamp", "")

                    # 根据事件类型显示不同的图标
                    icons = {
                        "start": "🟢",
                        "init": "🔧",
                        "info": "ℹ️",
                        "complete": "✅",
                        "error": "❌",
                        "heartbeat": "💓"
                    }
                    icon = icons.get(event_type, "📝")

                    if event_type != "heartbeat":  # 不显示心跳
                        print(f"{icon} [{event_type}] {content}")

                    # 如果收到完成或错误信号，结束监听
                    if event_type in ["complete", "error"]:
                        print("-" * 50)
                        print("🏁 流式输出结束")
                        break

                except json.JSONDecodeError:
                    print(f"⚠️ 无法解析数据: {event.data}")

    except requests.exceptions.ConnectionError:
        print("❌ 连接失败！请确保agent_server.py已启动")
    except Exception as e:
        print(f"❌ 发生错误: {e}")


def test_agent_stream_timeout():
    """测试SSE连接超时处理"""
    print("\n⏱️ 测试SSE连接超时...")
    session_id = "test-timeout-session"
    stream_url = f"http://powerai.cc:5120/stream/{session_id}"

    try:
        print(f"📡 连接不存在的SSE流: {stream_url}")
        sse_response = requests.get(stream_url, stream=True, timeout=5)
        client = sseclient.SSEClient(sse_response)

        count = 0
        for event in client.events():
            if event.data:
                data = json.loads(event.data)
                if data.get("type") == "heartbeat":
                    count += 1
                    print(f"💓 收到心跳 #{count}")
                    if count >= 3:  # 收到3个心跳后断开
                        print("🛑 主动断开连接")
                        break

    except Exception as e:
        print(f"⚠️ 预期的超时或连接错误: {e}")

if __name__ == "__main__":
    print("=== Agent Server SSE 测试 ===")

    # 检查依赖
    try:
        import sseclient
    except ImportError:
        print("❌ 缺少sseclient-py依赖，请运行: pip install sseclient-py")
        exit(1)

    # 1. 测试同步调用
    test_agent_sync()

    # 2. 测试流式调用
    # test_agent_stream()

    # 3. 测试超时处理
    # test_agent_stream_timeout()

    print("\n🎉 所有测试完成!")