from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import json
import time
import threading
import queue
import uuid
from dataclasses import dataclass, field

from config import dred, dgreen, dblue, dcyan, dyellow

from agent.base_tool import PROMPT_REACT
from agent.base_tool import Base_Tool
from agent.tool_agent import Tool_Agent

from agent.tools.folder_tool import Folder_Tool

from server_manager.web_server_task_manager import Web_Server_Task_Manager

app = Flask(__name__)
CORS(app)  # 启用跨域请求支持


@app.route('/api/start_agent_task', methods=['POST'])
def start_agent_task():
    try:
        data = request.json
        query = data.get('query', '')
        # tools = data.get('tools', [])
        base_url = data.get('base_url', 'https://api.deepseek.com/v1')
        api_key = data.get('api_key', 'sk-c1d34a4f21e3413487bb4b2806f6c4b8')

        tools = [Folder_Tool]
        # 创建agent实例
        agent = Tool_Agent(
            in_query=query,
            in_tool_classes=tools,
            # in_output_stream_buf=task_message_queue.put,  # 该设置在Web_Server_Task_Manager.start_task()中完成
            # in_output_stream_buf=dyellow,
            # in_output_stream_to_console=True,
            in_base_url=base_url,
            in_api_key=api_key,
        )

        session_id = str(uuid.uuid4())  # ------------------!!!!!!-------------------
        task_id = Web_Server_Task_Manager.start_task(
            task_obj=agent,
            session_id=session_id
        )

        # 返回task_id
        return jsonify({"task_id": task_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/get_agent_task_sse_stream', methods=['GET'])
def get_agent_task_sse_stream():
    try:
        task_id = request.args.get("task_id")

        return Response(
            Web_Server_Task_Manager.get_task_sse_stream_gen(task_id=task_id),
            mimetype='text/event-stream'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    # 直接返回HTML内容，而不是尝试读取文件
    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tool Agent SSE演示</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"], textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        .output {
            margin-top: 20px;
            border: 1px solid #ddd;
            padding: 15px;
            border-radius: 4px;
            background-color: #f9f9f9;
            min-height: 200px;
            white-space: pre-wrap;
        }
        .status {
            margin-top: 10px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Tool Agent SSE演示</h1>

        <div class="form-group">
            <label for="query">查询内容：</label>
            <textarea id="query" rows="3" placeholder="输入您的查询内容"></textarea>
        </div>

        <div class="form-group">
            <label for="base-url">API基础URL：</label>
            <input type="text" id="base-url" value="https://api.deepseek.com/v1">
        </div>

        <div class="form-group">
            <label for="api-key">API密钥：</label>
            <input type="text" id="api-key" value="sk-c1d34a4f21e3413487bb4b2806f6c4b8">
        </div>

        <button id="run-btn">运行</button>

        <div class="status">状态：<span id="status">空闲</span></div>

        <div class="output" id="output"></div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const runBtn = document.getElementById('run-btn');
            const outputEl = document.getElementById('output');
            const statusEl = document.getElementById('status');
            const queryEl = document.getElementById('query');
            const baseUrlEl = document.getElementById('base-url');
            const apiKeyEl = document.getElementById('api-key');

            let eventSource = null;

            runBtn.addEventListener('click', function() {
                // 清空之前的输出
                outputEl.textContent = '';

                // 更新状态
                statusEl.textContent = '处理中...';

                // 如果已有连接，关闭它
                if (eventSource) {
                    eventSource.close();
                }

                // 准备请求数据
                const requestData = {
                    query: queryEl.value,
                    tools: [], // 这里可以根据需要传入工具列表
                    base_url: baseUrlEl.value,
                    api_key: apiKeyEl.value
                };

                // 发送POST请求
                console.log('-------------------已发送/api/start_agent_task请求...--------------------------')
                fetch('/api/start_agent_task', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                }).then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json(); // 解析 JSON 数据
                })                
                .then(data => {
                    const task_id_from_server = data.task_id; // 后端返回的
                    console.log('task_id_from_server: ', task_id_from_server)

                    // 创建SSE连接
                    console.log('尝试创建SSE连接...')
                    // const eventSource = new EventSource('/api/get_agent_task_sse_stream?task_id=' + encodeURIComponent(task_id_from_server));
                    eventSource = new EventSource('/api/get_agent_task_sse_stream?task_id=' + encodeURIComponent(task_id_from_server));
                    console.log('创建SSE连接成功.')
                    console.log('eventSource: ', eventSource)

                    // 监听消息
                    eventSource.onmessage = function(event) {
                        console.log("收到SSE数据:", event.data);
                        const data = JSON.parse(event.data);

                        if (data['[done]']) {
                        // if (data.done) {
                            // 处理完成
                            statusEl.textContent = '完成';
                            eventSource.close();
                        } else if (data.message) {
                            // 追加消息到输出区域
                            outputEl.textContent += data.message;
                        }
                    };

                    // 监听错误
                    eventSource.onerror = function(error) {
                        statusEl.textContent = '错误';
                        console.error('SSE错误:', error);
                        eventSource.close();
                    };
                })
                .catch(error => {
                    statusEl.textContent = '错误';
                    console.error('请求错误:', error);
                });
            });
        });
    </script>
</body>
</html>"""
    return html_content


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)