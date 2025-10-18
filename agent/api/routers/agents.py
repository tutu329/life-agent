# app/routers/agents.py
from fastapi import APIRouter, HTTPException

from agent.core.agent_config import Agent_Config
from agent.core.protocol import Agent_Request_Result
from agent.core.agent_manager import Agent_Manager

import config

router = APIRouter()

@router.post("/get_web_socket_server_port")
def get_web_socket_server_port():
    res = config.Port.global_web_socket_server
    return res

@router.post("/get_all_mcp_tools")
def get_all_mcp_tools(mcp_url:str):
    res = Agent_Manager.get_mcp_url_tool_names(mcp_url=mcp_url)
    return res

@router.post("/get_all_local_tools")
def get_all_local_tools():
    res = Agent_Manager.get_local_all_tool_info_json()
    return res

@router.post("/create_agent", response_model=Agent_Request_Result)
def create_agent(agent_config: Agent_Config):
    res = Agent_Manager.create_agent(agent_config)
    if not res or not res.agent_id:
        raise HTTPException(status_code=500, detail=getattr(res, "result_string", "create failed"))
    return res

@router.post("/run_agent")
def run_agent(agent_id: str, query: str):
    res = Agent_Manager.run_agent(agent_id=agent_id, query=query)
    if res.result_type.name != "SUCCESS":
        raise HTTPException(status_code=409, detail=res.result_string or "run_agent failed")
    return {"ok": True, "agent_id": agent_id, "result_string": res.result_string}

@router.post("/get_agent_status")
def get_agent_status(agent_id: str):
    res = Agent_Manager.get_agent_status(agent_id=agent_id)
    if res.result_type.name != "SUCCESS":
        raise HTTPException(status_code=409, detail=res.result_string or "get_agent_status failed")
    return {"ok": True, "agent_id": agent_id, "result_content": res.result_content}