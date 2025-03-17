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
            # scheme_file_path='D:/server/life-agent/agent/agent_web_server/提纲.txt',
            scheme_file_path='Y:/life-agent/agent/agent_web_server/提纲.txt',
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
    # Return the improved HTML content with fixes for Word editor
    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>报告自主编制</title>
    <link href="https://cdn.quilljs.com/1.3.6/quill.snow.css" rel="stylesheet">
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
            height: calc(100vh - 40px); /* Account for the body padding */
        }
        .word-editor {
            flex: 2; /* Changed from 1 to 2 to make it 2/3 of the width */
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
            flex: 1; /* This remains 1 to make it 1/3 of the width */
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
            font-size: 16px; /* Small sanhao size (小三号) */
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
            padding-bottom: 20px; /* 增加底部内边距 */
            border-radius: 4px;
            background-color: #f9f9f9;
            flex-grow: 1; /* 自适应高度 */
            overflow-y: auto; /* 保持滚动条 */
            white-space: pre-wrap;
            font-size: 9px;
            box-sizing: border-box; /* 确保内边距计算正确 */
        }
        .status {
            margin-top: 10px;
            color: #666;
        }
        /* Word Editor-like styles */
        #editor-container {
            flex-grow: 1;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        #editor {
            flex-grow: 1;
            overflow-y: auto;
            border: 1px solid #ddd;
            background-color: white;
        }
        .ql-toolbar {
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        /* Font size styles that match actual Word sizes */
        .ql-size-small {
            font-size: 10px;
        }
        .ql-size-normal {
            font-size: 12px;
        }
        .ql-size-large {
            font-size: 16px;
        }
        .ql-size-huge {
            font-size: 20px;
        }
        /* Button alignment */
        .button-container {
            display: flex;
            justify-content: flex-end; /* Align button to the right */
            margin-bottom: 15px;
        }
        /* Control panel content layout */
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
    <script src="https://cdnjs.cloudflare.com/ajax/libs/FileSaver.js/2.0.5/FileSaver.min.js"></script>
    <script src="https://cdn.quilljs.com/1.3.6/quill.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/docx/5.0.2/docx.min.js"></script>
</head>
<body>
    <div class="main-container">
        <!-- Word编辑器部分 -->
        <div class="word-editor">
            <!-- Quill editor with Word-like toolbar -->
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
                        <label for="base-url">API基础URL：</label>
                        <input type="text" id="base-url" value="https://api.deepseek.com/v1">
                    </div>

                    <div class="form-group">
                        <label for="api-key">API密钥：</label>
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
            // Initialize Quill editor with Word-like toolbar options
            var quill = new Quill('#editor', {
                modules: {
                    toolbar: [
                        [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
                        ['bold', 'italic', 'underline', 'strike'],
                        [{ 'color': [] }, { 'background': [] }],
                        [{ 'align': [] }],
                        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                        ['link', 'image'],
                        ['clean']
                    ]
                },
                placeholder: '在此输入内容...',
                theme: 'snow'
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
                // Clear previous output
                outputEl.textContent = '';

                // Update status
                statusEl.textContent = '处理中...';

                // Close any existing connection
                if (eventSource) {
                    eventSource.close();
                }

                // Prepare request data
                const requestData = {
                    query: queryEl.value,
                    tools: [],
                    base_url: baseUrlEl.value,
                    api_key: apiKeyEl.value
                };

                // Send POST request
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

                    // Listen for output messages
                    eventSource.onmessage = function(event) {
                        console.log("收到SSE数据:", event.data);
                        const data = JSON.parse(event.data);

                        if (data['[done]']) {
                            // Processing complete
                            statusEl.textContent = '完成';
                            eventSource.close();
                        } else if (data.message) {
                            // --------------Append message to quill area--------------
                            // Insert message into Quill editor
                            // 获取编辑器内容长度，注意 -1 防止末尾换行
                            let cursorPosition = quill.getLength() - 1;

                            // 防止编辑器为空时报错
                            cursorPosition = cursorPosition < 0 ? 0 : cursorPosition;

                            // Insert message into Quill editor at correct position
                            quill.insertText(cursorPosition, data.message);

                            // 计算插入文本的长度
                            let insertedLength = data.message.length;

                            // 应用字体和字号（内联格式）
                            quill.formatText(cursorPosition, insertedLength, {
                              'font': 'SimSun',   // 设置字体为宋体
                              'size': '16px'      // 设置字号为小四，约16px
                            });

                            // 可选：移动光标到插入文本之后
                            quill.setSelection(cursorPosition + data.message.length, 0);
                        }
                    };

                    // Listen for errors
                    eventSource.onerror = function(error) {
                        statusEl.textContent = '错误';
                        console.error('SSE错误:', error);
                        eventSource.close();
                    };


                    thinking_eventSource = new EventSource('/api/get_agent_task_thinking_sse_stream?task_id=' + encodeURIComponent(task_id_from_server));
                    console.log('创建thinking SSE连接成功.');
                    console.log('thinking_eventSource: ', thinking_eventSource);

                    // Listen for thinking messages
                    thinking_eventSource.onmessage = function(event) {
                        console.log("收到thinking SSE数据:", event.data);
                        const data = JSON.parse(event.data);

                        if (data['[done]']) {
                            // Processing complete
                            statusEl.textContent = '完成';
                            thinking_eventSource.close();
                        } else if (data.message) {
                            // --------------Append message to output area--------------
                            //outputEl.textContent += data.message;      
                            let color = "green";    
                            outputEl.innerHTML += `<span style="color:${color}">${data.message}</span>`;
                            outputEl.scrollTop = outputEl.scrollHeight; // 自动滚动到底部             
                        }
                    };

                    // Listen for errors
                    thinking_eventSource.onerror = function(error) {
                        // statusEl.textContent = 'thinking stream错误';
                        console.error('thinking stream SSE错误:', error);
                        thinking_eventSource.close();
                    };

                    log_eventSource = new EventSource('/api/get_agent_task_log_sse_stream?task_id=' + encodeURIComponent(task_id_from_server));
                    console.log('创建log SSE连接成功.');
                    console.log('log_eventSource: ', log_eventSource);

                    // Listen for log messages
                    log_eventSource.onmessage = function(event) {
                        console.log("收到log SSE数据:", event.data);
                        const data = JSON.parse(event.data);

                        if (data['[done]']) {
                            // Processing complete
                            statusEl.textContent = '完成';
                            thinking_eventSource.close();
                        } else if (data.message) {
                            // --------------Append message to output area--------------
                            //outputEl.textContent += data.message;      
                            let color = "black";    
                            outputEl.innerHTML += `<span style="color:${color}">${data.message}</span>`;
                            outputEl.scrollTop = outputEl.scrollHeight; // 自动滚动到底部             
                        }
                    };

                    // Listen for errors
                    log_eventSource.onerror = function(error) {
                        // statusEl.textContent = 'log stream错误';
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