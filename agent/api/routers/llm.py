from fastapi import APIRouter, HTTPException
from fastapi import Body

from agent.core.llm_manager import LLM_Manager
from tools.llm.response_and_chatml_api_client import Response_Request
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
    llm_id = LLM_Manager.create_llm(llm_config=llm_config)
    return llm_id

@router.post("/run_llm")
def run_llm(
    llm_id: str = Body(...),
    query: str = Body(...),
    response_request: Response_Request = Body(...)
):
    LLM_Manager.run_llm(llm_id=llm_id, query=query, response_request=response_request)

@router.post("/wait_llm")
def wait_llm(llm_id: str):
    LLM_Manager.wait_llm(llm_id=llm_id)

@router.post("/cancel_llm_run")
def cancel_llm_run(llm_id: str):
    LLM_Manager.cancel_llm_run(llm_id=llm_id)

@router.post("/clear_llm_history")
def clear_llm_history(llm_id: str):
    LLM_Manager.clear_llm_history(llm_id=llm_id)