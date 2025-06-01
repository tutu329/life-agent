import requests
import json


def test_agent():
    """Python测试Agent服务器"""
    url = "http://powerai.cc:5120/run_agent"

    # 测试数据
    data = {
        "query": '请告诉我"file_to_find.txt"在"d:\\demo\\"文件夹的哪个具体文件夹中',
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
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("❌ 连接失败！请确保agent_server.py已启动")
    except Exception as e:
        print(f"❌ 发生错误: {e}")


if __name__ == "__main__":
    test_agent()