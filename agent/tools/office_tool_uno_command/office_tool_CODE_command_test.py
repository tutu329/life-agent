import asyncio
import time
import json, json5
import ast  # 引入ast模块用于安全地解析字符串为Python对象
from utils.web_socket_manager import get_websocket_manager


def main():
    """
    主函数，用于直接向前端EditorPanel发送Office操作指令，以测试WebSocket通信链路。
    """
    print('🚀 启动Office工具底层指令测试脚本...')

    # 1. 获取WebSocket管理器单例并启动服务器
    ws_manager = get_websocket_manager()
    ws_manager.start_server()
    time.sleep(1)  # 等待服务器线程启动

    # 根据新的 `Web_Socket_Manager` 调整服务器状态检查
    if not ws_manager.server_started:
        print("❌ WebSocket服务器启动失败，请检查端口5112是否被占用或有其他错误。")
        return
    else:
        # manager实例上没有host和port属性，简化打印信息
        print(f'✅ WebSocket服务器已启动，监听端口5112...')

    # 2. 等待前端客户端连接并注册agent_id
    agent_id = None
    print('⏳ 正在等待前端EditorPanel连接并注册agent_id...')

    timeout = 30  # 等待30秒
    start_time = time.time()

    while time.time() - start_time < timeout:
        # 使用新的 `get_connected_clients` 方法，替换旧的 `.clients` 访问
        registered_clients = ws_manager.get_connected_clients()

        if registered_clients:
            # 选择第一个连接的客户端进行测试
            agent_id = registered_clients[0]
            print(f"✅ 成功发现已连接的客户端! Agent ID: {agent_id}")
            break
        else:
            print("   ...尚未发现客户端，2秒后重试...")
            time.sleep(2)

    if not agent_id:
        print(f"❌ 在 {timeout} 秒内没有发现任何连接的前端客户端。")
        print("   请按以下步骤排查：")
        print("   1. 在浏览器中打开agent-web前端页面 (https://powerai.cc:5101)。")
        print("   2. 确保前端页面已加载完成，'报告编制'中的编辑器已显示。")
        print("   3. 检查浏览器开发者工具(F12)的控制台，确认WebSocket是否已连接到 wss://powerai.cc:5112。")
        return

    # --- 进入交互式指令循环 ---
    print("\n" + "=" * 50)
    print("🎉 进入原生指令(Raw Command)交互模式 🎉")
    print("💡 Operation固定为 'call_raw_command'。")
    print("💡 您只需输入完整的 Collabora postMessage 指令字典。")
    print("💡 输入 'quit' 可随时退出程序。")
    print("=" * 50 + "\n")

    while True:
        # 检查客户端是否仍然连接，使用新的 get_connected_clients 方法
        if agent_id not in ws_manager.get_connected_clients():
            print("🔌 客户端似乎已断开连接。请重新启动脚本并刷新前端页面。")
            break

        # 操作指令固定为 call_raw_command
        operation = 'call_raw_command'

        # 获取完整的 command data 字典
        print("📖 推荐使用更可靠的 .uno:InsertText 指令:")
        print(
            "   {'MessageId': 'Send_UNO_Command', 'Values': {'Command': '.uno:InsertText', 'Args': {'Text': {'type': 'string', 'value': '测试文本'}}}}")
        print("📖 (备选) Action_Paste 指令:")
        print(
            "   {'MessageId': 'Action_Paste', 'Values': {'Mimetype': 'text/plain;charset=utf-8', 'Data': '测试文本'}}")
        data_str = input("👉 请输入完整的 Collabora 指令字典: ")
        if data_str.lower() == 'quit':
            break

        try:
            # 使用ast.literal_eval安全地将字符串转为字典
            # data = ast.literal_eval(data_str)
            # if not isinstance(data, dict):
            #     print("❌ 错误：输入的内容不是一个有效的字典格式。请重试。\n")
            #     continue
            data = json5.loads(data_str)
        except (ValueError, SyntaxError) as e:
            print(f"❌ 错误：解析字典失败: {e}。")
            print("   请确保输入是有效的Python字典格式，例如：{'MessageId': 'Action_Paste', ...}\n")
            continue

        # 构建与前端`handleOfficeCommand`匹配的指令
        command = {
            'type': 'office_operation',
            'operation': operation,
            'agent_id': agent_id,
            'data': data,
            'timestamp': int(time.time() * 1000)
        }

        # 通过WebSocket管理器发送指令
        print(f"\n🚀 准备向 Agent ID '{agent_id}' 发送原生指令...")
        print(f"📋 指令内容: {json.dumps(command, indent=2, ensure_ascii=False)}")

        success, message = ws_manager.send_command(agent_id, command)

        if success:
            print(f"✅ 指令已成功发送。")
            print(f"💬 WebSocket管理器响应: {message}")
            print("👀 请检查浏览器中的文档以确认效果。\n")
        else:
            print(f"❌ 发送指令失败: {message}\n")

    print("🛑 测试脚本已退出。")
    # 在程序退出前，恢复原始的ssl方法，避免影响其他可能使用ssl的库。


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 测试脚本被用户手动中断。")
    except Exception as e:
        print(f"\n❌ 脚本发生未预料的错误: {e}")
        import traceback

        traceback.print_exc()