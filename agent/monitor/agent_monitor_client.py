# pip install websocket-client

import json
import ssl
import websocket  # 注意：库名叫 websocket-client，导入名是 websocket

import config

URL = "wss://powerai.cc:5115"  # 公共回声服务，便于本地测试

def on_open(ws):
    print("✅ on_open: 连接已建立")
    ws.send(json.dumps({"type": "register", "client_id": config.Agent.AGENT_MONITOR_WS_CLIENT_ID}))

def on_message(ws, message):
    print("📩 on_message:", message)

def on_error(ws, err):
    print("❌ on_error:", err)

def on_close(ws, close_status_code, close_msg):
    print(f"👋 on_close: code={close_status_code}, msg={close_msg}")

if __name__ == "__main__":
    app = websocket.WebSocketApp(
        URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    # ping_interval 可做保活；遇到断线可自行做重连循环
    # sslopt 禁用证书验证（如果证书链不完整）
    app.run_forever(
        ping_interval=20, 
        ping_timeout=10,
        sslopt={"cert_reqs": ssl.CERT_NONE}
    )
