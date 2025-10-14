# client_minimal.py
import requests
from pprint import pprint

from agent.core.agent_config import Agent_Config
import llm_protocol
import time

BASE_URL = "http://powerai.cc:8005"

def agent_create(
    agent_name: str,
    llm_profile: str = "qwen3_80b_instruct",
    allowed_local_tool_names=None,
    has_history: bool = True,
    mcp_requests=None,
):
    """
    调用 POST /agents 创建 agent
    - llm_profile 需与你服务端映射一致（例如: "qwen3_80b_instruct" 或 "local_120b_mxfp4"）
    """
    payload = {
        "agent_name": agent_name,
        "llm_profile": llm_profile,
        "has_history": has_history,
    }
    if allowed_local_tool_names is not None:
        payload["allowed_local_tool_names"] = allowed_local_tool_names
    if mcp_requests is not None:
        payload["mcp_requests"] = mcp_requests

    r = requests.post(f"{BASE_URL}/agents", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()  # {"agent_id": "xxx"}

def agent_run(agent_id: str, instruction: str):
    """
    调用 POST /agents/{agent_id}/run 启动执行（后台线程跑，接口立即返回）
    """
    payload = {"instruction": instruction}
    r = requests.post(f"{BASE_URL}/agents/{agent_id}/run", json=payload, timeout=60)
    if r.status_code == 409:
        print(f"[WARN] 该 agent 正在执行中：{r.text}")
    r.raise_for_status()
    return r.json()

def main():
    llm_c = llm_protocol.g_online_qwen3_next_80b_instruct
    agent_config = Agent_Config(
        # llm_config=llm_protocol.g_online_deepseek_chat,
        llm_config=llm_c,
        agent_name='agent level 2-Folder_Tool_Level_2',
        allowed_local_tool_names=['Folder_Tool'],
        as_tool_name='Folder_Tool_Level_2',
        as_tool_description='本工具用来在文件夹中搜索指定文件',
    )
    # print(f'agent_config: {agent_config}')
    r = requests.post(f"{BASE_URL}/agents", json=agent_config.model_dump(exclude_none=True), timeout=60)
    r.raise_for_status()

    # print(f'agents.create()结果: {r.json()}')

    agent_id = r.json()["agent_id"]
    query = '请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，需要遍历每一个子文件夹，一定能找到'
    r = requests.post(f"{BASE_URL}/agents/run", params={'agent_id':agent_id, 'query':query}, timeout=60)
    # print(f'agents.run()结果: {r.json()}')

    while True:
        r = requests.post(f"{BASE_URL}/agents/get_status", params={'agent_id': agent_id}, timeout=60)
        res = r.json()
        if res.get('result_content') and res['result_content'].get('final_answer') and res['result_content']['final_answer']:
            print(f"agents.run()结果: {res['result_content']['final_answer']}")
            break

        time.sleep(1)


if __name__ == "__main__":
    main()