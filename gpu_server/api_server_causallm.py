# -*-coding:utf-8-*-
'''
git clone https://huggingface.co/TheBloke/CausalLM-14B-GPTQ
D:\models\CausalLM-14B-GPTQ
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
import asyncio

from llm_server_wrapper import CausalLM_Wrapper

from pydantic import BaseModel
from typing import Any, Dict, List, Literal, Optional, Union

class Stream_Response(BaseModel):
    delta: str
    finish_reason: Optional[Literal['stop', 'length']]

class CausalLM_Fastapi_Server():
    def __init__(self) -> None:
        self.llm = CausalLM_Wrapper()

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

    # def stream(self,
    #         message,
    #         temperature=0.7,
    #         top_p=0.95,
    #         top_k=40,
    #         repetition_penalty=1.1,
    #         max_new_tokens=512,
    #         stop=["</s>"],
    # ):
    #     return self.llm.generate(
    #         message=self.llm.get_prompt(message),
    #         # message=message,
    #         temperature=temperature,
    #         top_p=top_p,
    #         top_k=top_k,
    #         repetition_penalty=repetition_penalty,
    #         max_new_tokens=max_new_tokens,
    #         stop=stop,
    #     )

def start_server(model_wrapper, http_address: str, port: int):
# def start_server(model_wrapper, http_address: str, port: int, gpu_id: str):
#     os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
    # os.environ['CUDA_VISIBLE_DEVICES'] = gpu_id

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

    @app.post("/stream", response_model=Stream_Response)
    async def answer_question_stream(arg_dict: dict):
        # def decorate(generator):
        #     for item in generator:
        #         yield ServerSentEvent(json.dumps(item, ensure_ascii=False), event='delta')

        try:
            # print('=================server0==================')
            message = arg_dict["message"]
            temperature = arg_dict["temperature"]
            top_p = arg_dict["top_p"]
            top_k = arg_dict["top_k"]
            repetition_penalty = arg_dict["repetition_penalty"]
            max_new_tokens = arg_dict["max_new_tokens"]
            stop = arg_dict["stop"]
            # print('=================server1==================')

            res=EventSourceResponse(
                predict(
                    message,
                    temperature,
                    top_p,
                    top_k,
                    repetition_penalty,
                    max_new_tokens,
                    stop,
                ),
                media_type='text/event-stream'
            )
            # res=EventSourceResponse(
            #     decorate(model_wrapper.generate(
            #         message,
            #         temperature,
            #         top_p,
            #         top_k,
            #         repetition_penalty,
            #         max_new_tokens,
            #         stop,
            #     )),
            #     media_type='text/event-stream'
            # )
            print('=================server2==================')
            return res

        except Exception as e:
            print(f"/stream error: {e}")
            return f'LLM服务器错误: "{e}"'

    # predict主要是用于把sync的generate()改造为async函数，否则client调用会卡死
    async def predict(message,
                      temperature,
                      top_p,
                      top_k,
                      repetition_penalty,
                      max_new_tokens,
                      stop,
                      ):
        for chunk in model_wrapper.generate(
            message,
            temperature,
            top_p,
            top_k,
            repetition_penalty,
            max_new_tokens,
            stop,
        ):
            res = Stream_Response(delta=chunk, finish_reason=None)    #finish_reason只能为'stop'或'length'，不然只能为None
            yield '{}'.format(res.model_dump_json(exclude_unset=True))     #返回非'b'的正常字符串
            # await asyncio.sleep(0.0001)
        res = Stream_Response(delta='', finish_reason='stop')
        yield '{}'.format(res.model_dump_json(exclude_unset=True))
        # await asyncio.sleep(0.0001)

    print(f'starting server with url {http_address}:{port} ...')
    uvicorn.run(app=app, host=http_address, port=port, workers=1)

def main():
    model_wrapper = CausalLM_Wrapper()
    model_wrapper.init()
    print(model_wrapper.get_prompt('{}'))

    parser = argparse.ArgumentParser(description=f'Stream API Service for {model_wrapper.model_name}')
    # parser.add_argument('--device', '-d', help='device，-1 means cpu, other means gpu ids', default='0')
    parser.add_argument('--host', '-H', help='host to listen', default='0.0.0.0')
    parser.add_argument('--port', '-P', help='port of this service', default=8000)
    parser.add_argument(
        "--gpu", type=int, default=0, help="指定的GPU ID: 0、1等"
    )
    args = parser.parse_args()

    # import os
    # os.environ["CUDA_VISIBLE_DEVICES"] = f'{args.gpu}'

    start_server(model_wrapper, args.host, int(args.port))

if __name__ == '__main__':
    main()