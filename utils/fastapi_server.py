from typing import Callable, Dict, List, Type
import functools
from pydantic import BaseModel, Field, ConfigDict
from fastapi import FastAPI
import asyncio, queue
from sse_starlette.sse import EventSourceResponse  # pip install sse-starlette

from config import dblue, dyellow, dgreen, dcyan, dred

# ------------ ❷ 通用的 SSE 生成器 ----------------
class _GenDone: pass
GeneratorDone = _GenDone()  # 特殊标记，用来告诉生成器结束

async def _queue_streamer(q: queue.Queue):
    """把线程里写进 Queue 的内容转成 SSE"""
    loop = asyncio.get_running_loop()
    while True:
        # 阻塞队列读取要放在线程池，避免卡住 event loop
        # item = await loop.run_in_executor(None, lambda: q.get(timeout=1))
        # item = await loop.run_in_executor(None, q.get)
        # item = await q.get()
        item = await loop.run_in_executor(None, q.get)
        if item is GeneratorDone:
            break
        # print(f'--------------------q.get(): "{item}"---------------------------')
        yield {"data": item}

class FastAPI_Endpoint_With_SSE_Result:
    def __init__(self, id: str, stream_queues: Dict):
        self.id = id
        self.stream_queues = stream_queues

# ------------ 装饰器：把长过程(如agent执行过程)用fast_api挂载 --------------
# 1、 task_func挂载到：  /api/{task_func}
# 2、 sse-stream挂载到： /api/{task_func}/stream/{stream_id}/{stream_name}
def FastAPI_Endpoint_With_SSE(
        app: FastAPI,
        return_type: Type,                  # 告诉装饰器，被装饰函数的返回类型
        return_id_name: str,                # 告诉装饰器，被装饰函数的返回变量中，哪个字段是id
        return_stream_queues_name: str,     # 告诉装饰器，被装饰函数的返回变量中，哪个字段是stream_queues
):
    """
    用法:
        @FastAPI_Endpoint_With_SSE(app)
        def start_agent_sse_task(queues, some, args): ...
    """

    def decorator(task_func: Callable[..., return_type]):
        base_route = f"/api/{task_func.__name__}"

        @functools.wraps(task_func)
        async def start_endpoint(*args, **kwargs):
            """启动任务并返回 ID"""
            rtn = await task_func(*args, **kwargs)

            # 将结果存储在内存中（实际应用中可能需要使用 Redis 或数据库）
            result_id = rtn.dict()[return_id_name]
            stream_queues = rtn.dict()[return_stream_queues_name]

            # dred(f'stream_queues: "{stream_queues}"')
            # dred(f'type of stream_queues.output: "{type(stream_queues["output"])}"')

            # 存储到全局变量（生产环境建议使用 Redis）
            if not hasattr(app.state, 'active_streams'):
                app.state.active_streams = {}
            app.state.active_streams[result_id] = stream_queues

            # 只返回 ID，不返回 EventSourceResponse
            return {"id": result_id, "streams": list(stream_queues.keys())}

        async def stream_endpoint(stream_id: str, stream_name: str):
            """SSE 流端点"""
            if not hasattr(app.state, 'active_streams'):
                return {"error": "No active streams"}

            if stream_id not in app.state.active_streams:
                return {"error": "Stream not found"}

            stream_queues = app.state.active_streams[stream_id]
            if stream_name not in stream_queues:
                return {"error": "Stream name not found"}

            return EventSourceResponse(_queue_streamer(stream_queues[stream_name]))

        # 注册两个路由
        app.post(base_route)(start_endpoint)  # 启动任务
        app.get(f"{base_route}/stream/{{stream_id}}/{{stream_name}}")(stream_endpoint)  # SSE 流
        return task_func
    return decorator

# 显示所有挂载的路由、以及GET/POST情况
def fastapi_show_all_routes(app: FastAPI):
    print(f'--------------------FastAPI服务器所挂载的所有路由-----------------------------')
    for r in app.routes:
        if hasattr(r, 'methods'):
            print(f'{list(r.methods)} {r.path}')
    print(f'-------------------/FastAPI服务器所挂载的所有路由-----------------------------')
# from typing import Callable, Dict, List, Type
# import functools
# from pydantic import BaseModel, Field, ConfigDict
# from fastapi import FastAPI
# import asyncio, queue
# from sse_starlette.sse import EventSourceResponse   # pip install sse-starlette
#
# # ------------ ❷ 通用的 SSE 生成器 ----------------
# class _GenDone: pass
# GeneratorDone = _GenDone()      # 特殊标记，用来告诉生成器结束
#
# async def _queue_streamer(q: queue.Queue):
#     """把线程里写进 Queue 的内容转成 SSE"""
#     loop = asyncio.get_running_loop()
#     while True:
#         # 阻塞队列读取要放在线程池，避免卡住 event loop
#         item = await loop.run_in_executor(None, q.get)
#         if item is GeneratorDone:
#             break
#         yield {"data": item}
#
# # class FastAPI_Endpoint_With_SSE_Result(BaseModel):
# #     id                          :str                            # 如: agent_id
# #     event_source_response_dict  :Dict[str, EventSourceResponse] # 所有streams的一个dict
# #
# #     # 开启“任意类型”支持
# #     model_config = ConfigDict(arbitrary_types_allowed=True)
#
# class FastAPI_Endpoint_With_SSE_Result:
#     id                          :str                            # 如: agent_id
#     event_source_response_dict  :Dict[str, EventSourceResponse] # 所有streams的一个dict
#
# # ------------ 装饰器：把任意长任务函数挂到 /api/<func_name> --------------
# def FastAPI_Endpoint_With_SSE(
#     app: FastAPI,
#     return_type: Type,                  # 告诉装饰器，被装饰函数的返回类型
#     return_id_name:str,                 # 告诉装饰器，被装饰函数的返回变量中，哪个字段是id（id通常为后端动态生成对象的唯一id，如:'agent_id'）
#     return_stream_queues_name:str,      # 告诉装饰器，被装饰函数的返回变量中，哪个字段是stream_queues（stream_queues是与后台对象如id对应agent绑定的sse输出通道）
# ):
# # )-> Callable[..., FastAPI_Endpoint_With_SSE_Result]:    # 整个被装饰结果返回的类型
#     """
#     用法:
#         @FastAPI_Endpoint_With_SSE(app)
#         def start_agent_sse_task(queues, some, args): ...
#     """
#     def decorator(task_func: Callable[..., return_type]):
#         route = f"/api/{task_func.__name__}"
#         @functools.wraps(task_func)  # 保留原函数的 __name__/__doc__，对调试和 IDE 友好
#         async def endpoint(*args, **kwargs):    # 使用 *args 和 **kwargs 来接收任何额外的参数
#             rtn = await task_func(*args, **kwargs)
#
#             # 为每条流构建一个 EventSourceResponse
#             event_source_response_dict = {
#                 name: EventSourceResponse(_queue_streamer(queue))
#                     for name, queue in rtn.dict()[return_stream_queues_name].items()
#             }
#
#             # 返回 id + 多流字典
#             # fastapi_result = FastAPI_Endpoint_With_SSE_Result(
#             #     id = rtn.dict()[return_id_name],
#             #     event_source_response_dict=event_source_response_dict
#             # )
#             fastapi_result = {
#                 'id': rtn.dict()[return_id_name],
#                 'event_source_response_dict':event_source_response_dict
#             }
#             return fastapi_result
#
#         # 动态注册到 FastAPI
#         app.post(route)(endpoint)
#         return task_func
#     return decorator
#
# # 显示所有挂载的路由、以及GET/POST情况
# def fastapi_show_all_routes(app: FastAPI):
#     print(f'--------------------FastAPI服务器所挂载的所有路由-----------------------------')
#     for r in app.routes:
#         if hasattr(r, 'methods'):
#             print(f'{list(r.methods)} {r.path}')
#     print(f'-------------------/FastAPI服务器所挂载的所有路由-----------------------------')