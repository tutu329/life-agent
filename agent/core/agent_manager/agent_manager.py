from agent.core.mcp.mcp_manager import get_mcp_server_tools, get_mcp_server_tool_names
from agent.core.agent_config import Agent_Config
from agent.core.toolcall_agent import Toolcall_Agent

def main():
    from openai import OpenAI
    import httpx
    import llm_protocol
    import config

    server_url1 = "https://powerai.cc:8011/mcp/sqlite/sse"
    server_url2 = "http://localhost:8789/sse"
    # server_url = "https://powerai.cc:8011/mcp/everything/sse"
    tools = get_mcp_server_tools(server_url1) +  get_mcp_server_tools(server_url2)
    tool_names = get_mcp_server_tool_names(server_url1) + get_mcp_server_tool_names(server_url2)
    print(tool_names)
    # print(tools)
    # for tool in tools:
    #     print(tool)

    agent_config = Agent_Config(
        agent_name='MCP agent',
        tool_names=tool_names,
        tool_objects=tools,
        # llm_config=llm_protocol.g_online_groq_gpt_oss_20b,
        # llm_config=llm_protocol.g_online_groq_gpt_oss_120b,
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4,
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4_lmstudio,
        # llm_config=llm_protocol.g_online_qwen3_next_80b_instruct,
        # llm_config=llm_protocol.g_online_qwen3_next_80b_thinking,
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4,
        llm_config=llm_protocol.g_local_gpt_oss_120b_mxfp4_lmstudio,
        # llm_config=llm_protocol.g_local_qwen3_30b_gptq_int4,
        has_history=True,
    )
    agent = Toolcall_Agent(agent_config=agent_config)
    agent.init()
    # agent.run(query='列出所有表格名称', tools=tools)
    # agent.run(query='查看通信录表的数据', tools=tools)

    while True:
        agent.run(query=input('请输入你的指令：'))

if __name__ == "__main__":
    main()