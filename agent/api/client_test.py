import requests, time
from agent.core.agent_config import Agent_Config
from agent.core.mcp.protocol import MCP_Server_Request
import llm_protocol

BASE_URL = "http://powerai.cc:8005"

def main():
    # ------------------------------ 0.1、get_all_local_tools() -> List[tool_info] ------------------------------
    r = requests.post(f"{BASE_URL}/agents/get_all_local_tools", timeout=60)
    r.raise_for_status()
    tools_info = r.json()
    print('------------------get_all_local_tools-----------------------')
    for tool_info in tools_info:
        print(tool_info)
    print('-----------------/get_all_local_tools-----------------------')

    # ------------------------------ 0.2、get_all_mcp_tools() -> List[tool_name] ------------------------------
    r = requests.post(f"{BASE_URL}/agents/get_all_mcp_tools", params={'mcp_url':'https://powerai.cc:8011/mcp/sqlite/sse'}, timeout=60)
    r.raise_for_status()
    tool_names = r.json()
    print('------------------get_all_mcp_tools-----------------------')
    print(tool_names)
    print('-----------------/get_all_mcp_tools-----------------------')

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
    # ------------------------------ 1.1、create 底层agent1 as tool ------------------------------
    agent_config = Agent_Config(
        llm_config=llm_c,
        agent_name='agent level 2-Folder_Tool_Level_2',
        allowed_local_tool_names=['Folder_Tool'],
        as_tool_name='Folder_Tool_Level_2',
        as_tool_description='本工具用来在文件夹中搜索指定文件',
    )
    r = requests.post(f"{BASE_URL}/agents/create_agent", json=agent_config.model_dump(exclude_none=True), timeout=60)
    r.raise_for_status()
    agent_id = r.json()["agent_id"]
    print(f'sub-agent as tool(agent_id: {agent_id!r}) created.')

    # ------------------------------ 1.2、create 底层agent2 as tool ------------------------------
    mcp_requests = [
        # MCP_Server_Request(url="https://powerai.cc:8011/mcp/sqlite/sse").model_dump(exclude_none=True),
        MCP_Server_Request(url="https://powerai.cc:8011/mcp/sqlite/sse", allowed_tool_names=['list_tables', 'read_query']).model_dump(exclude_none=True),
        MCP_Server_Request(url="http://localhost:8789/sse", allowed_tool_names=['tavily-search']).model_dump(exclude_none=True),
        MCP_Server_Request(url="http://localhost:8788/sse").model_dump(exclude_none=True),
    ]
    agent_config = Agent_Config(
        llm_config=llm_c,
        agent_name='agent level 2-List_Table_Tool_Level_2',
        allowed_local_tool_names=['List_Table_Tool'],
        mcp_requests=mcp_requests,
        as_tool_name='List_Table_Tool_Level_2',
        as_tool_description='本工具用来查询数据库中有哪些表格',
    )
    r = requests.post(f"{BASE_URL}/agents/create_agent", json=agent_config.model_dump(exclude_none=True), timeout=60)
    r.raise_for_status()
    agent_id = r.json()["agent_id"]
    print(f'sub-agent as tool(agent_id: {agent_id!r}) created.')

    # ------------------------------ 1.3、create 上层agent(可以叠加若干层) ------------------------------
    agent_config = Agent_Config(
        llm_config=llm_c,
        agent_name='agent level 1',
        allowed_local_tool_names=['Folder_Tool_Level_2', 'List_Table_Tool_Level_2'],   # 关键参数，通过'Folder_Tool_Level_2'这个字符串，指定1.1注册的agent作为tool
    )
    r = requests.post(f"{BASE_URL}/agents/create_agent", json=agent_config.model_dump(exclude_none=True), timeout=60)
    r.raise_for_status()
    agent_id = r.json()["agent_id"]
    print(f'upper-agent(agent_id: {agent_id!r}) created.')

    # ------------------------------ 2、run_agent(agent_id) 运行上层agent------------------------------
    query = '请告诉我有哪些表格'
    # query = '请告诉我/home/tutu/demo下的哪个子目录里有file_to_find.txt这个文件，需要遍历每一个子文件夹，一定能找到'
    r = requests.post(f"{BASE_URL}/agents/run_agent", params={'agent_id':agent_id, 'query':query}, timeout=60)

    while True:
        # ------------------------------ 3、get_agent_status(agent_id) ------------------------------
        res = requests.post(f"{BASE_URL}/agents/get_agent_status", params={'agent_id': agent_id}, timeout=60).json()
        if res.get('result_content') and res['result_content'].get('final_answer') and res['result_content']['final_answer']:
            print(f"upper-agent(agent_id={agent_id!r})返回结果: {res['result_content']['final_answer']!r}")
            break

        time.sleep(1)

if __name__ == "__main__":
    main()