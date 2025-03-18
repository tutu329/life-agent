from flask import Flask, request, jsonify, Response, session
from flask_cors import CORS
import json
import time
import threading
import uuid
from dataclasses import dataclass, field

# Import your existing modules
import config
from config import dred, dgreen, dblue, dcyan, dyellow
from agent.base_tool import PROMPT_REACT
from agent.base_tool import Base_Tool
from agent.tool_agent import Tool_Agent
from agent.tools.folder_tool import Folder_Tool
from agent.tools.table_tool import Table_Tool
from server_manager.web_server_task_manager import Web_Server_Task_Manager

from client.office.office_client import Web_Office_Write

app = Flask(__name__)
CORS(app)  # Enable CORS support

# Secret key for session
app.secret_key = 'tj112279_seaver'


# Create anonymous session ID for each client
@app.before_request
def ensure_session_id():
    """
    Create and store a 'session_id' before each request if it doesn't exist.
    """
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())


@app.route('/api/start_agent_task', methods=['POST'])
def start_agent_task():
    try:
        data = request.json
        query = data.get('query', '')
        base_url = data.get('base_url', 'https://api.deepseek.com/v1')
        api_key = data.get('api_key', 'sk-c1d34a4f21e3413487bb4b2806f6c4b8')

        # tools = [Folder_Tool, Table_Tool]
        # Create agent instance
        agent = Web_Office_Write(
            scheme_file_path='D:/server/life-agent/agent/agent_web_server/提纲_13900.txt',
            # scheme_file_path='Y:/life-agent/agent/agent_web_server/提纲.txt',
            base_url=base_url,
            api_key=api_key,
            temperature=config.LLM_Default.temperature
        )

        # Get client's anonymous session ID
        session_id = session.get('session_id')
        dblue(f'client login (session_id: "{session_id}").')

        # Start task
        task_id = Web_Server_Task_Manager.start_task(
            task_obj=agent,
            session_id=session_id
        )

        # Return task_id
        return jsonify({"task_id": task_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/get_agent_task_output_sse_stream', methods=['GET'])
def get_agent_task_output_sse_stream():
    try:
        task_id = request.args.get("task_id")

        return Response(
            Web_Server_Task_Manager.get_task_output_sse_stream_gen(task_id=task_id),
            mimetype='text/event-stream'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/get_agent_task_thinking_sse_stream', methods=['GET'])
def get_agent_task_thinking_sse_stream():
    try:
        task_id = request.args.get("task_id")

        return Response(
            Web_Server_Task_Manager.get_task_thinking_sse_stream_gen(task_id=task_id),
            mimetype='text/event-stream'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/get_agent_task_log_sse_stream', methods=['GET'])
def get_agent_task_log_sse_stream():
    try:
        task_id = request.args.get("task_id")

        return Response(
            Web_Server_Task_Manager.get_task_log_sse_stream_gen(task_id=task_id),
            mimetype='text/event-stream'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/')
def index():
    # Return the improved HTML content with CKEditor5 replacing Quill editor
    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>报告自主编制</title>
    <!-- 移除 Quill CSS -->
    <!-- <link href="https://cdn.quilljs.com/1.3.6/quill.snow.css" rel="stylesheet"> -->
    <!-- 引入 CKEditor5 Classic Build -->
    <script src="https://cdn.ckeditor.com/ckeditor5/39.0.1/classic/ckeditor.js"></script>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            height: 100vh;
            overflow: hidden;
            box-sizing: border-box;
        }
        .main-container {
            display: flex;
            max-width: 1200px;
            margin: 0 auto;
            gap: 20px;
            height: calc(100vh - 40px);
        }
        .word-editor {
            flex: 2;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            height: 100%;
            box-sizing: border-box;
            overflow: hidden;
        }
        .control-panel {
            flex: 1;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            height: 100%;
            box-sizing: border-box;
        }
        h1 {
            color: #333;
            text-align: center;
            font-size: 16px;
            margin-top: 0;
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
            margin-right: 10px;
        }
        button:hover {
            background-color: #45a049;
        }
        .output {
            margin-top: 20px;
            border: 1px solid #ddd;
            padding: 15px;
            padding-bottom: 20px;
            border-radius: 4px;
            background-color: #f9f9f9;
            flex-grow: 1;
            overflow-y: auto;
            white-space: pre-wrap;
            font-size: 9px;
            box-sizing: border-box;
        }
        .status {
            margin-top: 10px;
            color: #666;
        }
        /* CKEditor 容器样式 */
        #editor-container {
            flex-grow: 1;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        /* 保证 CKEditor 实例全屏展示 */
        #editor {
            flex-grow: 1;
            overflow-y: auto;
            border: 1px solid #ddd;
            background-color: white;
        }
        .button-container {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 15px;
        }
        .control-panel-content {
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            height: 100%;
            overflow: hidden;
        }
        .control-panel-inputs {
            flex-shrink: 0;
        }
    </style>
</head>
<body>
    <div class="main-container">
        <!-- Word编辑器部分 -->
        <div class="word-editor">
            <!-- CKEditor 容器 -->
            <div id="editor-container">
                <div id="editor"></div>
            </div>
        </div>

        <!-- 控制面板部分 -->
        <div class="control-panel">
            <div class="control-panel-content">
                <div class="control-panel-inputs">
                    <h1>报告自主编制</h1>

                    <div class="form-group">
                        <label for="query">查询内容：</label>
                        <textarea id="query" rows="3" placeholder="输入您的查询内容"></textarea>
                    </div>

                    <div class="form-group">
                        <label for="base-url">API Base-URL：</label>
                        <input type="text" id="base-url" value="https://api.deepseek.com/v1">
                    </div>

                    <div class="form-group">
                        <label for="api-key">API-key：</label>
                        <input type="text" id="api-key" value="sk-c1d34a4f21e3413487bb4b2806f6c4b8">
                    </div>

                    <div class="button-container">
                        <button id="run-btn">运行</button>
                    </div>

                    <div class="status">状态：<span id="status">空闲</span></div>
                </div>

                <div class="output" id="output"></div>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // 初始化 CKEditor5
            ClassicEditor
                .create(document.querySelector('#editor'))
                .then(editorInstance => {
                    window.editor = editorInstance;
                })
                .catch(error => {
                    console.error(error);
                });

            const runBtn = document.getElementById('run-btn');
            const outputEl = document.getElementById('output');
            const statusEl = document.getElementById('status');
            const queryEl = document.getElementById('query');
            const baseUrlEl = document.getElementById('base-url');
            const apiKeyEl = document.getElementById('api-key');

            let eventSource = null;

            // Run SSE task
            runBtn.addEventListener('click', function() {
                // 清空之前的输出
                outputEl.textContent = '';

                // 更新状态
                statusEl.textContent = '处理中...';

                // 关闭任何已存在的连接
                if (eventSource) {
                    eventSource.close();
                }

                // 准备请求数据
                const requestData = {
                    query: queryEl.value,
                    tools: [],
                    base_url: baseUrlEl.value,
                    api_key: apiKeyEl.value
                };

                console.log('-------------------已发送/api/start_agent_task请求...--------------------------');
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
                    return response.json();
                })
                .then(data => {
                    const task_id_from_server = data.task_id;
                    console.log('task_id_from_server: ', task_id_from_server);
                    console.log('尝试创建SSE连接...');

                    eventSource = new EventSource('/api/get_agent_task_output_sse_stream?task_id=' + encodeURIComponent(task_id_from_server));
                    console.log('创建SSE连接成功.');
                    console.log('eventSource: ', eventSource);

                    // 监听输出消息
                    eventSource.onmessage = function(event) {
                        console.log("收到SSE数据:", event.data);
                        const data = JSON.parse(event.data);

                        if (data['[done]']) {
                            statusEl.textContent = '完成';
                            eventSource.close();
                        } else if (data.message) {
                            // 将消息追加到 CKEditor 内容末尾
                            if (window.editor) {
                                window.editor.model.change(writer => {
                                    const root = window.editor.model.document.getRoot();
                                    const insertPosition = window.editor.model.createPositionAt(root, 'end');
                                    writer.insertText(data.message, {}, insertPosition);
                                });
                            } 
                        }
                    };

                    eventSource.onerror = function(error) {
                        statusEl.textContent = '错误';
                        console.error('SSE错误:', error);
                        eventSource.close();
                    };

                    let thinking_eventSource = new EventSource('/api/get_agent_task_thinking_sse_stream?task_id=' + encodeURIComponent(task_id_from_server));
                    console.log('创建thinking SSE连接成功.');
                    console.log('thinking_eventSource: ', thinking_eventSource);

                    thinking_eventSource.onmessage = function(event) {
                        console.log("收到thinking SSE数据:", event.data);
                        const data = JSON.parse(event.data);

                        if (data['[done]']) {
                            statusEl.textContent = '完成';
                            thinking_eventSource.close();
                        } else if (data.message) {
                            let color = "green";    
                            outputEl.innerHTML += '<span style="color:' + color + '">' + data.message + '</span>';
                            outputEl.scrollTop = outputEl.scrollHeight;
                        }
                    };

                    thinking_eventSource.onerror = function(error) {
                        console.error('thinking stream SSE错误:', error);
                        thinking_eventSource.close();
                    };

                    let log_eventSource = new EventSource('/api/get_agent_task_log_sse_stream?task_id=' + encodeURIComponent(task_id_from_server));
                    console.log('创建log SSE连接成功.');
                    console.log('log_eventSource: ', log_eventSource);

                    log_eventSource.onmessage = function(event) {
                        console.log("收到log SSE数据:", event.data);
                        const data = JSON.parse(event.data);

                        if (data['[done]']) {
                            statusEl.textContent = '完成';
                            log_eventSource.close();
                        } else if (data.message) {
                            let color = "black";    
                            outputEl.innerHTML += '<span style="color:' + color + '">' + data.message + '</span>';
                            outputEl.scrollTop = outputEl.scrollHeight;
                        }
                    };

                    log_eventSource.onerror = function(error) {
                        console.error('log stream SSE错误:', error);
                        log_eventSource.close();
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
