from typing import Callable, Dict, List, Type
import functools
from pydantic import BaseModel, Field, ConfigDict
from fastapi import FastAPI
import asyncio, queue
from sse_starlette.sse import EventSourceResponse   # pip install sse-starlette

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

class FastAPI_Endpoint_With_SSE_Result(BaseModel):
    id                          :str                            # 如: agent_id
    event_source_response_dict  :Dict[str, EventSourceResponse] # 所有streams的一个dict

    # 开启“任意类型”支持
    model_config = ConfigDict(arbitrary_types_allowed=True)

# ------------ 装饰器：把任意长任务函数挂到 /api/<func_name> --------------
def FastAPI_Endpoint_With_SSE(
    app: FastAPI,
    rtn_id_name:str,                # 告诉装饰器，被装饰函数的返回变量中，哪个字段是id
    rtn_stream_queues_name:str,     # 告诉装饰器，被装饰函数的返回变量中，哪个字段是stream_queues
    return_type: Type,              # 告诉装饰器，被装饰函数的返回类型
)-> Callable[..., FastAPI_Endpoint_With_SSE_Result]:    # 整个被装饰结果返回的类型
    """
    用法:
        @FastAPI_Endpoint(app)
        def start_agent(queues, some, args): ...
    """
    def decorator(task_func: Callable[..., return_type]):
        route = f"/api/{task_func.__name__}"
        @functools.wraps(task_func)  # 保留原函数的 __name__/__doc__，对调试和 IDE 友好
        async def endpoint():
            rtn = task_func()

            # 为每条流构建一个 EventSourceResponse
            event_source_response_dict = {
                name: EventSourceResponse(_queue_streamer(queue))
                    for name, queue in rtn.dict()[rtn_stream_queues_name].items()
            }

            # 返回 id + 多流字典
            fastapi_result = FastAPI_Endpoint_With_SSE_Result(
                id = rtn.dict()[rtn_id_name],
                event_source_response_dict=event_source_response_dict
            )
            return fastapi_result

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
