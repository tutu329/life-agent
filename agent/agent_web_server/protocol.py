from typing import Callable, Dict, List
from pydantic import BaseModel, Field, ConfigDict
from concurrent.futures import ThreadPoolExecutor, Future
from fastapi import FastAPI
import asyncio, queue
from sse_starlette.sse import EventSourceResponse   # pip install sse-starlette

from agent.core.multi_agent_server import Registered_Agent_Data

# ------------ ❷ 通用的 SSE 生成器 ----------------
class _GenDone: pass
GeneratorDone = _GenDone()      # 特殊标记，用来告诉生成器结束

async def _queue_streamer(q: queue.Queue):
    """把线程里写进 Queue 的内容转成 SSE"""
    loop = asyncio.get_running_loop()
    while True:
        # 阻塞队列读取要放在线程池，避免卡住 event loop
        item = await loop.run_in_executor(None, q.get)
        if item is GeneratorDone:
            break
        yield {"data": item}

# ------------ 装饰器：把任意长任务函数挂到 /api/<func_name> --------------
def FastAPI_Endpoint(
    app: FastAPI,
):
    """
    用法:
        @FastAPI_Endpoint(app)
        def start_agent(queues, some, args): ...
    """
    def decorator(task_func: Callable[..., None]):
        route = f"/api/{task_func.__name__}"

        async def endpoint():
            rtn:Registered_Agent_Data = None
            rtn = task_func()

            # 为每条流构建一个 EventSourceResponse
            event_source_response_dict = {
                name: EventSourceResponse(_queue_streamer(queue))
                    for name, queue in rtn.agent_stream_queues.items()
            }

            # 返回 id + 多流字典
            return {
                "id":rtn.agent_id,
                "event_source_response_dict":event_source_response_dict
            }

        # 动态注册到 FastAPI
        app.post(route)(endpoint)
        return task_func
    return decorator

# 显示所有挂载的路由、以及GET/POST情况
def fastapi_show_all_routes(app: FastAPI):
    print(f'--------------------FastAPI服务器所挂载的所有路由-----------------------------')
    for r in app.routes:
        if hasattr(r, 'methods'):
            print(f'{list(r.methods)} {r.path}')
    print(f'-------------------/FastAPI服务器所挂载的所有路由-----------------------------')
