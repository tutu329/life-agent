# client_minimal.py
import requests
from pprint import pprint

from agent.core.agent_config import Agent_Config
import llm_protocol
import time

BASE_URL = "http://powerai.cc:8005"

def main():
    # ------------------------------ 1、create_agent() -> agent_id ------------------------------
    llm_c = llm_protocol.g_online_qwen3_next_80b_instruct
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
    agent_config = Agent_Config(
        llm_config=llm_c,
        agent_name='agent level 2-Folder_Tool_Level_2',
        allowed_local_tool_names=['Folder_Tool'],
        as_tool_name='Folder_Tool_Level_2',
        as_tool_description='本工具用来在文件夹中搜索指定文件',
    )
    r = requests.post(f"{BASE_URL}/agents/create_agent", json=agent_config.model_dump(exclude_none=True), timeout=60)
    r.raise_for_status()


    # ------------------------------ 2、run_agent(agent_id) ------------------------------
    agent_id = r.json()["agent_id"]
    query = '请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，需要遍历每一个子文件夹，一定能找到'
    r = requests.post(f"{BASE_URL}/agents/run_agent", params={'agent_id':agent_id, 'query':query}, timeout=60)
    # print(f'agents.run()结果: {r.json()}')

    while True:
        # ------------------------------ 3、get_agent_status(agent_id) ------------------------------
        r = requests.post(f"{BASE_URL}/agents/get_agent_status", params={'agent_id': agent_id}, timeout=60)
        res = r.json()
        if res.get('result_content') and res['result_content'].get('final_answer') and res['result_content']['final_answer']:
            print(f"agents.run()结果: {res['result_content']['final_answer']}")
            break

        time.sleep(1)

if __name__ == "__main__":
    main()