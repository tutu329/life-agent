from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse

import sys
from pydantic import BaseModel
import uvicorn

import asyncio
import json
import uuid
from typing import Dict
import queue
import threading

from config import Port

# agent
from agent.agent_config import Config
from agent.tool_agent import Tool_Agent

# tools
from agent.tools.folder_tool import Folder_Tool
from agent.tools.human_console_tool import Human_Console_Tool

from config import dred,dgreen,dyellow,dblue,dcyan

app = FastAPI(title="Agent FastAPI Server")

# 添加CORS支持，允许JavaScript调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局存储SSE连接
sse_connections: Dict[str, queue.Queue] = {}

def safe_encode(text):
    """安全编码文本，处理特殊字符"""
    # 用于解决报错：UnicodeEncodeError: 'utf-8' codec can't encode characters in position 71-78: surrogates not allowed
    if isinstance(text, str):
        # 移除或替换代理对字符
        try:
            # 尝试编码为UTF-8并解码，清理无效字符
            text = text.encode('utf-8', 'ignore').decode('utf-8')
            # 替换代理对字符
            text = text.encode('utf-8', 'replace').decode('utf-8')
        except Exception:
            text = repr(text)  # 如果还有问题，转为字符串表示
    return text

class Agent_Request(BaseModel):
    query: str
    base_url: str = "http://powerai.cc:28001/v1"
    api_key: str = "empty"
    model_id: str = ""

@app.get("/")
def root():
    return {"server status": "Agent FastAPI Server 运行中..."}


@app.get("/stream/{session_id}")
async def stream_events(session_id: str):
    """SSE流式输出端点"""

    async def event_stream():
        # 创建队列用于存储流式数据
        if session_id not in sse_connections:
            sse_connections[session_id] = queue.Queue()

        q = sse_connections[session_id]

        try:
            while True:
                try:
                    # 从队列获取数据，设置超时避免阻塞
                    data = q.get(timeout=1)
                    if data == "CLOSE":  # 结束信号
                        break

                    # 安全编码数据
                    if isinstance(data, dict) and 'content' in data:
                        data['content'] = safe_encode(data['content'])

                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    # 发送心跳保持连接
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': str(asyncio.get_event_loop().time())})}\n\n"
                    await asyncio.sleep(0.1)
        finally:
            # 清理连接
            if session_id in sse_connections:
                del sse_connections[session_id]

    return StreamingResponse(
        event_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

def stream_callback(session_id: str, data: dict):
    """流式回调函数，将数据推送到SSE队列"""
    if session_id in sse_connections:
        try:
            # 确保数据安全编码
            safe_data = data.copy()
            if 'content' in safe_data:
                safe_data['content'] = safe_encode(safe_data['content'])

            sse_connections[session_id].put(safe_data, timeout=1)
        except queue.Full:
            print(f"SSE队列已满，丢弃数据: {session_id}")


class StreamCapture:
    """捕获标准输出流，用于捕获agent的打印输出"""

    def __init__(self, callback, session_id):
        self.callback = callback
        self.session_id = session_id
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def __enter__(self):
        sys.stdout = self
        sys.stderr = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

    def write(self, text):
        # 写入原始输出
        self.original_stdout.write(text)
        # 同时发送到SSE流
        if text.strip():  # 只发送非空内容
            self.callback(self.session_id, {
                "type": "output",
                "content": safe_encode(text.strip())
            })

    def flush(self):
        self.original_stdout.flush()

@app.post("/run_agent_sync")
def run_agent_sync(request: Agent_Request):
    """运行Agent"""
    # 创建工具列表
    tools = [Human_Console_Tool, Folder_Tool]

    # 创建配置
    config = Config(
        base_url=request.base_url,
        api_key=request.api_key,
        model_id=request.model_id
    )

    agent = Tool_Agent(
        query=request.query,
        tool_classes=tools,
        agent_config=config
    )

    # 初始化和运行
    # 同步运行
    try:
        agent.init()
        success = agent.run()
        dyellow('--------------------------33---------------------------')
        dyellow(f'result: "{agent.final_answer}"')
        rtn_dict = {
            "success": success,
            "query": request.query
        }
        clean_bytes = json.dumps(rtn_dict, ensure_ascii=False).encode("utf-8", "surrogatepass")
        dyellow('--------------------------3---------------------------')
        return JSONResponse(content=json.loads(clean_bytes))
        # return rtn_dict
    except UnicodeEncodeError as e:
        return {
            "success": False,
            "query": request.query,
            "error": f"Unicode编码错误: {safe_encode(str(e))}"
        }
    except Exception as e:
        return {
            "success": False,
            "query": request.query,
            "error": safe_encode(str(e))
        }

@app.post("/run_agent")
def run_agent(request: Agent_Request):
    """运行Agent"""
    session_id = str(uuid.uuid4())  # 生成唯一会话ID
    dyellow(f'request(session_id="{session_id}"): {request}')

    # 创建工具列表
    tools = [Human_Console_Tool, Folder_Tool]

    # 创建配置
    config = Config(
        base_url=request.base_url,
        api_key=request.api_key
    )

    # 创建并运行Agent
    agent = Tool_Agent(
        tool_classes=tools,
        agent_config=config,
        query=request.query
    )

    # 初始化和运行
    agent.init()
    success = agent.run()

    # -------------------------初始化SSE连接-------------------------
    sse_connections[session_id] = queue.Queue()

    # 设置流式回调
    def stream_handler(content, step_type="info"):
        stream_callback(session_id, {
            "type": step_type,
            "content": safe_encode(str(content)),
            "timestamp": str(asyncio.get_event_loop().time())
        })

    # 假设agent有set_stream方法
    if hasattr(agent, 'set_stream'):
        agent.set_stream(stream_handler)
    # ------------------------/初始化SSE连接-------------------------

    # ----------------------在后台线程运行agent，避免阻塞----------------------
    def run_agent_background():
        try:
            stream_callback(session_id, {"type": "start", "content": "Agent开始运行"})

            with StreamCapture(stream_callback, session_id):
                # 初始化和运行
                agent.init()
                stream_callback(session_id, {"type": "init", "content": "Agent初始化完成"})
                success = agent.run()

            stream_callback(session_id, {
                "type": "complete",
                "content": f"Agent运行完成，结果: {success}"
            })
            # 发送结束信号
            stream_callback(session_id, "CLOSE")

        except UnicodeEncodeError as e:
            error_msg = f"Unicode编码错误: {str(e)}"
            stream_callback(session_id, {
                "type": "error",
                "content": safe_encode(error_msg)
            })
            stream_callback(session_id, "CLOSE")
            print(f"Unicode错误已处理: {error_msg}")

        except Exception as e:
            error_msg = f"Agent运行出错: {str(e)}"
            stream_callback(session_id, {
                "type": "error",
                "content": safe_encode(error_msg)
            })
            stream_callback(session_id, "CLOSE")
            print(f"Agent错误: {error_msg}")
    # ---------------------/在后台线程运行agent，避免阻塞----------------------

    # 在后台线程运行
    threading.Thread(target=run_agent_background, daemon=True).start()
    return {
        "success": True,
        "query": request.query,
        "session_id": session_id,
        "stream_url": f"/stream/{session_id}",
        "message": "Agent正在后台运行，请通过stream_url获取实时输出"
    }

    # return {
    #     "success": success,
    #     "query": request.query
    # }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=Port.agent_fastapi_server)
