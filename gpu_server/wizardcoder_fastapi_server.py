# -*-coding:utf-8-*-
'''
File Name:chatglm2-6b-stream-api.py
Author:Luofan
Time:2023/6/26 13:33
'''

import os
import sys
import json
import torch
import uvicorn
import logging
import argparse
from fastapi import FastAPI
from transformers import AutoTokenizer, AutoModel
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import ServerSentEvent, EventSourceResponse

from llm_model_wrapper import Wizardcoder_Wrapper

class Wizaardcoder_Fastapi_Server():
    def __init__(self) -> None:
        self.llm = Wizardcoder_Wrapper()

    def init(self):
        self.llm.init()

    # def clear(self) -> None:
    #     if torch.cuda.is_available():
    #         with torch.cuda.device(f"cuda:{args.device}"):
    #             torch.cuda.empty_cache()
    #             torch.cuda.ipc_collect()

    # def answer(self, query: str, history):
    #     response, history = self.model.chat(self.tokenizer, query, history=history)
    #     history = [list(h) for h in history]
    #     return response, history

    def stream(self,
            message,
            temperature=0.7,
            top_p=0.9,
            top_k=10,
            repetition_penalty=1.1,
            max_new_tokens=2048,
            stop=["</s>"],
    ):
        return self.llm.generate(
            message=message,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repetition_penalty=repetition_penalty,
            max_new_tokens=max_new_tokens,
            stop=stop,
        )

def start_server(model_wrapper, http_address: str, port: int, gpu_id: str):
    os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
    os.environ['CUDA_VISIBLE_DEVICES'] = gpu_id

    app = FastAPI()
    app.add_middleware(CORSMiddleware,
                       allow_origins=["*"],
                       allow_credentials=True,
                       allow_methods=["*"],
                       allow_headers=["*"])
    @app.get("/")
    def index():
        return {f'FastAPI server: {model_wrapper.model_name}'}
        # return {'message': 'started', 'success': True}

    @app.post("/stream")
    def answer_question_stream(arg_dict: dict):
        def decorate(generator):
            for item in generator:
                yield ServerSentEvent(json.dumps(item, ensure_ascii=False), event='delta')

        try:
            message = arg_dict["message"]
            temperature = arg_dict["temperature"]
            top_p = arg_dict["top_p"]
            top_k = arg_dict["top_k"]
            repetition_penalty = arg_dict["repetition_penalty"]
            max_new_tokens = arg_dict["max_new_tokens"]
            stop = arg_dict["stop"]

            return EventSourceResponse(decorate(model_wrapper.stream(
                message,
                temperature,
                top_p,
                top_k,
                repetition_penalty,
                max_new_tokens,
                stop,
            )))
        except Exception as e:
            print(f"/stream error: {e}")
            return f'LLM服务器错误: "{e}"'

    print(f'starting server with url {http_address}:{port} ...')
    uvicorn.run(app=app, host=http_address, port=port, workers=1)

def main():
    model_wrapper = Wizardcoder_Wrapper()
    model_wrapper.init()

    parser = argparse.ArgumentParser(description=f'Stream API Service for {model_wrapper.model_name}')
    parser.add_argument('--device', '-d', help='device，-1 means cpu, other means gpu ids', default='0')
    parser.add_argument('--host', '-H', help='host to listen', default='0.0.0.0')
    parser.add_argument('--port', '-P', help='port of this service', default=8000)
    args = parser.parse_args()
    start_server(model_wrapper, args.host, int(args.port), args.device)

def main_client():
    pass

if __name__ == '__main__':
    main()
    # main_client()