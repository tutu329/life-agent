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

        tools = [Folder_Tool]
        # Create agent instance
        agent = Web_Office_Write(
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
    # Return the improved HTML content with fixes for Word editor
    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tool Agent SSE演示</title>
    <link href="https://cdn.quilljs.com/1.3.6/quill.snow.css" rel="stylesheet">
    <style>
        body {
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .main-container {
            display: flex;
            max-width: 1200px;
            margin: 0 auto;
            gap: 20px;
        }
        .word-editor {
            flex: 1;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            min-height: 600px;
        }
        .control-panel {
            flex: 1;
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
            margin-right: 10px;
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
        /* Word Editor-like styles */
        #editor {
            height: 500px;
            margin-bottom: 20px;
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
        /* Custom font size toolbar */
        .font-size-toolbar {
            display: flex;
            padding: 8px;
            background: #f0f0f0;
            align-items: center;
            margin-bottom: 10px;
        }
        .font-size-label {
            margin-right: 8px;
            font-weight: bold;
        }
        .font-style-label {
            margin-right: 8px;
            margin-left: 16px;
            font-weight: bold;
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
            <h1>Word文档编辑器</h1>

            <!-- Custom font controls -->
            <div class="font-size-toolbar">
                <span class="font-style-label">字体:</span>
                <select id="font-style-selector">
                    <option value="SimSun">宋体</option>
                    <option value="SimHei" selected>黑体</option>
                    <option value="Microsoft YaHei">微软雅黑</option>
                    <option value="KaiTi">楷体</option>
                    <option value="FangSong">仿宋</option>
                    <option value="Arial">Arial</option>
                    <option value="Times New Roman">Times New Roman</option>
                </select>

                <span class="font-size-label" style="margin-left: 15px;">字号:</span>
                <select id="font-size-selector">
                    <option value="42px">初号 (42px)</option>
                    <option value="36px">小初 (36px)</option>
                    <option value="26px">一号 (26px)</option>
                    <option value="24px">小一 (24px)</option>
                    <option value="22px">二号 (22px)</option>
                    <option value="18px">小二 (18px)</option>
                    <option value="16px">三号 (16px)</option>
                    <option value="15px">小三 (15px)</option>
                    <option value="14px" selected>四号 (14px)</option>
                    <option value="12px">小四 (12px)</option>
                    <option value="10.5px">五号 (10.5px)</option>
                    <option value="9px">小五 (9px)</option>
                </select>

                <button id="save-btn" style="margin-left: 15px;">保存为Word</button>
            </div>

            <!-- Quill editor with Word-like toolbar -->
            <div id="editor"></div>
        </div>

        <!-- 控制面板部分 -->
        <div class="control-panel">
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

            const fontStyleSelector = document.getElementById('font-style-selector');
            const fontSizeSelector = document.getElementById('font-size-selector');
            const saveBtn = document.getElementById('save-btn');
            const runBtn = document.getElementById('run-btn');
            const outputEl = document.getElementById('output');
            const statusEl = document.getElementById('status');
            const queryEl = document.getElementById('query');
            const baseUrlEl = document.getElementById('base-url');
            const apiKeyEl = document.getElementById('api-key');

            let eventSource = null;

            // Apply font style changes
            function applyFontStyle() {
                const fontFamily = fontStyleSelector.value;
                quill.format('font', fontFamily);

                // Global application of font family to editor
                document.querySelector('.ql-editor').style.fontFamily = fontFamily;
            }

            // Apply font size changes
            function applyFontSize() {
                const fontSize = fontSizeSelector.value;

                // Global application of font size to editor
                document.querySelector('.ql-editor').style.fontSize = fontSize;
            }

            // Initial font settings
            applyFontStyle();
            applyFontSize();

            // Event listeners for font changes
            fontStyleSelector.addEventListener('change', applyFontStyle);
            fontSizeSelector.addEventListener('change', applyFontSize);

            // Save as Word document
            saveBtn.addEventListener('click', function() {
                const editorContent = document.querySelector('.ql-editor').innerHTML;
                const editorText = document.querySelector('.ql-editor').innerText;
                const fontSize = parseInt(fontSizeSelector.value);
                const fontFamily = fontStyleSelector.value;

                // Create a new Word document
                const doc = new docx.Document({
                    sections: [{
                        properties: {},
                        children: [
                            new docx.Paragraph({
                                children: [
                                    new docx.TextRun({
                                        text: editorText,
                                        size: fontSize * 2, // Convert px to docx size
                                        font: {
                                            name: fontFamily
                                        }
                                    })
                                ]
                            })
                        ]
                    }]
                });

                // Generate and download the Word file
                docx.Packer.toBlob(doc).then(blob => {
                    saveAs(blob, "document.docx");
                    alert("Word文档已保存!");
                }).catch(err => {
                    console.error("保存文档时出错:", err);
                    alert("保存文档时出错，请查看控制台获取详情。");
                });
            });

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

                    eventSource = new EventSource('/api/get_agent_task_sse_stream?task_id=' + encodeURIComponent(task_id_from_server));
                    console.log('创建SSE连接成功.');
                    console.log('eventSource: ', eventSource);

                    // Listen for messages
                    eventSource.onmessage = function(event) {
                        console.log("收到SSE数据:", event.data);
                        const data = JSON.parse(event.data);

                        if (data['[done]']) {
                            // Processing complete
                            statusEl.textContent = '完成';
                            eventSource.close();
                        } else if (data.message) {
                            // Append message to output area
                            outputEl.textContent += data.message;

                            // Insert message into Quill editor
                            const cursorPosition = quill.getLength();
                            quill.insertText(cursorPosition, data.message);

                            // Apply current font settings to newly inserted text
                            quill.formatText(
                                cursorPosition, 
                                data.message.length, 
                                {
                                    'font': fontStyleSelector.value
                                }
                            );
                        }
                    };

                    // Listen for errors
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