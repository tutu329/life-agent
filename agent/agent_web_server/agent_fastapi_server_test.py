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