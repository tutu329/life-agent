from fastapi import APIRouter, HTTPException

from tools.llm.response_and_chatml_api_client import Response_and_Chatml_LLM_Client
from llm_protocol import LLM_Config
import config

router = APIRouter()

@router.post("/get_web_socket_server_port")
def get_web_socket_server_port():
    res = config.Port.global_llm_socket_server
    return res

@router.post("/create_llm")
def create_llm(llm_config:LLM_Config):
    client = Response_and_Chatml_LLM_Client()
    client.init()
    llm_id = client.llm_id
    return llm_id

@router.post("/run_llm")
def run_llm(agent_id: str, query: str):
    res = Agent_Manager.run_agent(agent_id=agent_id, query=query)
    if res.result_type.name != "SUCCESS":
        raise HTTPException(status_code=409, detail=res.result_string or "run_agent failed")
    return {"ok": True, "agent_id": agent_id, "result_string": res.result_string}
