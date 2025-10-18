import requests, time
from agent.core.agent_config import Agent_Config
from agent.core.mcp.protocol import MCP_Server_Request
from tools.llm.response_and_chatml_api_client import Response_Request

import llm_protocol

BASE_URL = "http://powerai.cc:8005"

# 向web_socket_server注册agent_id(仅agent_id能对应到本client)
def register_web_socket_and_run_forever(llm_id, port, url="wss://powerai.cc"):
    import json
    import ssl

    # pip install websocket-client
    import websocket  # 注意：库名叫 websocket-client，导入名是 websocket

    URL = url + f':{port}'  # 公共回声服务，便于本地测试

    def on_open(ws):
        print("✅ on_open: 连接已建立")
        ws.send(json.dumps({"type": "register", "client_id": llm_id}))

    def on_message(ws, message):
        print("📩 on_message:", message)

    app = websocket.WebSocketApp(
        URL,
        on_open=on_open,
        on_message=on_message,
    )
    # ping_interval 可做保活；遇到断线可自行做重连循环
    # sslopt 禁用证书验证（如果证书链不完整）
    app.run_forever(
        ping_interval=20,
        ping_timeout=10,
        sslopt={"cert_reqs": ssl.CERT_NONE}
    )

SHOW_WEBSOCKET_CALLBACK_MESSAGES = True
# SHOW_WEBSOCKET_CALLBACK_MESSAGES = False

def main():
    # ---------获取web_socket_server的port---------
    port = requests.post(f"{BASE_URL}/llm/get_web_socket_server_port", timeout=60).json()
    print(f'【web_socket_server的port】{port!r}')

    # ------------------------------ 1、create_llm() -> agent_id ------------------------------
    llm_config = llm_protocol.g_online_qwen3_next_80b_instruct
    # g_online_qwen3_next_80b_instruct = LLM_Config(
    #     name='qwen3_next_80b_instruct',
    #     base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
    #     api_key=os.getenv("QWEN_API_KEY") or 'empty',
    #     llm_model_id='qwen3-next-80b-a3b-instruct',
    #     temperature=0.7,
    #     top_p=0.8,
    #     chatml=True,
    #     max_new_tokens=8192,
    #     stream=True,
    # )
    # ------------------------------ 1、create llm ------------------------------
    llm_id = requests.post(f"{BASE_URL}/llm/create_llm", json=llm_config.model_dump(exclude_none=True), timeout=60).json()
    print(f'llm(llm_id: {llm_id!r}) created.')

    # query='写一首长诗，2000字'
    query='我叫土土'

    response_request = Response_Request(
        model=llm_config.llm_model_id,
        temperature=llm_config.temperature,
        top_p=llm_config.top_p,
        max_output_tokens=llm_config.max_new_tokens,
        # reasoning={"effort": llm_config.reasoning_effort},
        stream=True,
    ).model_dump(exclude_none=True)
    json = {
        'llm_id': llm_id,
        'query': query,
        'response_request': response_request,
    }
    requests.post(f"{BASE_URL}/llm/run_llm", json=json, timeout=60).json()
    requests.post(f"{BASE_URL}/llm/wait_llm", params={'llm_id':llm_id}, timeout=60).json()

    if SHOW_WEBSOCKET_CALLBACK_MESSAGES:
        register_web_socket_and_run_forever(llm_id, port)

    # time.sleep(3)


if __name__ == "__main__":
    main()