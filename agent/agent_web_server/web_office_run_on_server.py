from flask import Flask, request, jsonify, Response, session
from flask_cors import CORS
import json
import time
import threading
import uuid
import queue
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

from tools.llm.api_client import LLM_Client, Async_LLM

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
        model = data.get('model', '')  # Get the model value from request data
        dblue(f'-------------------------query-------------------------')
        dblue(f'{query!r}')
        dblue(f'------------------------/query-------------------------')
        dblue(f'-------------------------model-------------------------')
        dblue(f'{model!r}')
        dblue(f'------------------------/model-------------------------')

        if model=='V3模型':
            base_url = 'https://api.deepseek.com/v1'
            api_key = 'sk-c1d34a4f21e3413487bb4b2806f6c4b8'
            model_id = 'deepseek-chat'
        elif model=='R1模型':
            base_url = 'https://api.deepseek.com/v1'
            api_key = 'sk-c1d34a4f21e3413487bb4b2806f6c4b8'
            model_id = 'deepseek-reasoner'
        elif model=='72B模型':
            base_url = 'https://powerai.cc:8001/v1'
            api_key = 'empty'
            model_id = ''

        # Create agent instance
        agent = None

        if query:
            llm = LLM_Client(url=base_url, api_key=api_key, model_id=model_id)
            prompt = f'''以下是用户的问题或请求：
<用户的问题或请求>
{query}
</用户的问题或请求>
请根据其内容判断其诉求，并选择以下之一进行回复：
<回复的可选内容>
直接问答
通过工具问答
编制报告
</回复的可选内容>
<回复要求>
不能进行任何解释，直接回复可选项的内容
不要加任何引号、括号等修饰
</回复要求>
'''
            gen = llm.ask_prepare(question=prompt, temperature=0).get_result_generator()
            answer = ''
            for chunk in gen:
                answer += chunk
                dyellow(chunk, end='', flush=True)
            dyellow()

            dred('-----------------用户意图-----------------------')
            dred(answer)
            dred('----------------/用户意图-----------------------')

            if answer == '直接问答' or '@' in query:
                question = f'''请根据以下的用户问题，按要求回答:
<用户问题>
{query}
</用户问题>
<回答要求>
1、由于你的回答是输出到word环境中，因此你的回答绝对不能用markdown格式。
2、你的输出内容如果涉及层次内容，各个层级的标题要用"一、"、"二、"、"三、"、"1、"、"2、"、"3、"以及"(1)"、"(2)"、"(3)"这类，如果没有层次化内容，不要用这些标题。
</回答要求>
'''
                # ----------------------特例----------------------
                if '@' in query:
                    from agent.agent_web_server.temp_table_data import table_analysis_string, table_35kv_company_string
                    if '@电力行业统计调查制度调查表-目录表(中电联)' in query:
                        query = query.split('\n')[-1]
                        dred(f'------query------')
                        dred(query)
                        dred(f'------query------')
                        question=f'''
请严格根据表格内容和回答要求，回答用户问题: 
<用户问题>
{query}
</用户问题>
<回答要求>
1、由于你的回答是输出到word环境中，因此你的回答绝对不能用markdown格式。
2、你的输出内容如果涉及层次内容，各个层级的标题要用"一、"、"二、"、"三、"、"1、"、"2、"、"3、"以及"(1)"、"(2)"、"(3)"这类，如果没有层次化内容，不要用这些标题。
</回答要求>
<表格内容>
{table_analysis_string}
</表格内容>
'''
                        dyellow(question)

                    elif '@电量平衡情况表(公司-杭州) @电网负荷特性表(公司-杭州) @全社会用电分类情况表(公司-杭州)' in query:
                        query = query.split('\n')[-1]
                        dred(f'------query------')
                        dred(query)
                        dred(f'------query------')
                        question = f'''
请严格根据表格内容和回答要求，回答用户问题: 
<用户问题>
{query}
</用户问题>
<回答要求>
1、由于你的回答是输出到word环境中，因此你的回答绝对不能用markdown格式。
2、你的输出内容如果涉及层次内容，各个层级的标题要用"一、"、"二、"、"三、"、"1、"、"2、"、"3、"以及"(1)"、"(2)"、"(3)"这类，如果没有层次化内容，不要用这些标题。
</回答要求>
<表格内容>
{table_35kv_company_string}
</表格内容>
'''
                        dyellow(question)

                # ---------------------/特例----------------------

                agent = Async_LLM(
                    question=question,
                    url=base_url,
                    api_key=api_key,
                    model_id=model_id,
                    temperature=0.6,
                    is_web_server=True,
                )
                session_id = session.get('session_id')
                dblue(f'client login (session_id: "{session_id}").')

                # Start task
                task_id = Web_Server_Task_Manager.start_task(
                    task_obj=agent,
                    session_id=session_id
                )

                dblue(f'task_id: "{task_id}"')
                return jsonify({"task_id": task_id})
            elif answer == '通过工具问答':
                tools = [Table_Tool]
                agent = Tool_Agent(
                    query=query,
                    in_base_url=base_url,
                    in_api_key=api_key,
                    in_model_id='',
                    in_temperature=0.6,
                    tool_classes=tools,
                    is_web_server=True,
                )

                session_id = session.get('session_id')
                task_id = Web_Server_Task_Manager.start_task(
                    task_obj=agent,
                    session_id=session_id
                )
                return jsonify({"task_id": task_id})
            elif answer == '编制报告':
                agent = Web_Office_Write(
                    # scheme_file_path='D:/server/life-agent/agent/agent_web_server/提纲_13900.txt',
                    scheme_file_path='Y:/life-agent/agent/agent_web_server/提纲.txt',
                    base_url=base_url,
                    api_key=api_key,
                    model_id='',
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
            else:
                return None

    except Exception as e:
        return jsonify({"start_agent_task error": str(e)}), 500


@app.route('/api/get_agent_task_output_sse_stream', methods=['GET'])
def get_agent_task_output_sse_stream():
    try:
        task_id = request.args.get("task_id")

        return Response(
            Web_Server_Task_Manager.get_task_output_sse_stream_gen(task_id=task_id),
            mimetype='text/event-stream'
        )

    except Exception as e:
        return jsonify({"get_agent_task_output_sse_stream error": str(e)}), 500


@app.route('/api/get_agent_task_thinking_sse_stream', methods=['GET'])
def get_agent_task_thinking_sse_stream():
    try:
        task_id = request.args.get("task_id")

        return Response(
            Web_Server_Task_Manager.get_task_thinking_sse_stream_gen(task_id=task_id),
            mimetype='text/event-stream'
        )

    except Exception as e:
        return jsonify({"get_agent_task_thinking_sse_stream error": str(e)}), 500


@app.route('/api/get_agent_task_log_sse_stream', methods=['GET'])
def get_agent_task_log_sse_stream():
    try:
        task_id = request.args.get("task_id")

        return Response(
            Web_Server_Task_Manager.get_task_log_sse_stream_gen(task_id=task_id),
            mimetype='text/event-stream'
        )

    except Exception as e:
        return jsonify({"get_agent_task_log_sse_stream error": str(e)}), 500


@app.route('/api/get_task_tool_client_data_sse_stream', methods=['GET'])
def get_task_tool_client_data_sse_stream():
    try:
        task_id = request.args.get("task_id")

        return Response(
            Web_Server_Task_Manager.get_task_tool_client_data_sse_stream_gen(task_id=task_id),
            mimetype='text/event-stream'
        )

    except Exception as e:
        return jsonify({"get_task_tool_client_data_sse_stream error": str(e)}), 500


@app.route('/')
def index():
    # Return the improved HTML content with CKEditor5 replacing Quill editor
    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>电力看经济研究咨询平台</title>
    <!-- 引入 CKEditor5 -->
    <script src="https://cdn.ckeditor.com/ckeditor5/39.0.1/decoupled-document/ckeditor.js"></script>
    <!-- 引入 jsTree -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jstree/3.3.12/themes/default/style.min.css" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jstree/3.3.12/jstree.min.js"></script>
    <style>
        /* ********** 通用布局部分 ********** */
        body {
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            /* 保证页面可用区域是可计算的固定高度，这里用 100vh - 40px 做演示 */
            height: 100vh;
            overflow: hidden;
            box-sizing: border-box;
        }
        .main-container {
            /* 让主容器本身有确定的高度，从 body 继承： */
            height: calc(100vh - 40px);
            display: flex;
            max-width: 2000px;
            margin: 0 auto;
            gap: 20px;
            box-sizing: border-box;
        }

        /* ********** 左侧树状结构面板 ********** */
        .tree-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            min-height: 0;
            overflow: hidden;
        }
        .tree-panel h2 {
            margin: 0 0 15px 0;
            font-size: 16px;
            color: #333;
        }
        #jstree-container {
            flex: 1;
            overflow: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            background: #fff;
        }
        /* 自定义表格节点的图标 */
        .jstree-default .jstree-icon.jstree-themeicon-custom {
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23666' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='3' width='18' height='18' rx='2' ry='2'%3E%3C/rect%3E%3Cline x1='3' y1='9' x2='21' y2='9'%3E%3C/line%3E%3Cline x1='3' y1='15' x2='21' y2='15'%3E%3C/line%3E%3C/svg%3E");
            background-size: 16px 16px;
            background-repeat: no-repeat;
            background-position: center;
            width: 16px;
            height: 16px;
            margin-right: 4px;
        }

        /* ********** CKEditor 中间编辑区 ********** */
        .word-editor {
            flex: 2;                
            display: flex;          
            flex-direction: column; 
            box-sizing: border-box;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            min-height: 0;
            border: 1px solid #ddd;
        }

        /* ********** 右侧控制面板部分 ********** */
        .control-panel {
            flex: 1;                
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
            min-height: 0; /* 同理，避免高度被"撑开" */

            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
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
        input[type="text"],
        textarea {
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
            padding: 8px 12px;  /* 减小按钮内边距 */
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;    /* 减小按钮字体大小 */
            margin-right: 10px;
        }
        button:hover {
            background-color: #45a049;
        }
        button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }

        /* ********** 右侧面板内的输出 ********** */
        .control-panel-content {
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            min-height: 0; /* 避免被挤压时的高度问题 */
            overflow: hidden;
        }
        .control-panel-inputs {
            flex-shrink: 0;
        }
        .output {
            margin-top: 20px;
            border: 1px solid #ddd;
            padding: 15px 20px;
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
            font-size: 12px;  /* 减小状态标签字体大小 */
        }
        .status-label {
            font-size: 12px;  /* 减小"状态："文字的字体大小 */
        }
        .button-container {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 15px;
        }

        /* ********** CKEditor 填满父容器并滚动的关键 ********** */
        #editor-container {
            /* 让父容器可弹性伸缩，占满 .word-editor 中除去 padding 的剩余空间 */
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0; /* 避免"被子元素撑高" */
            border: 1px solid #ddd;
            border-radius: 4px;
            overflow: hidden;
        }
        /* CKEditor 最高父级 (.ck.ck-editor) 也要让它自适应伸缩 */
        .ck.ck-editor {
            display: flex;
            flex-direction: column;
            flex: 1;
            min-height: 0;
        }
        /* 让主编辑区 .ck.ck-editor__main 可以继续填满剩余空间 */
        .ck.ck-editor__main {
            display: flex;
            flex-direction: column;
            flex: 1;
            min-height: 0; /* 允许被挤压 */
        }
        /* 最终在可滚动的编辑区里打开滚动条 */
        .ck-editor__editable {
            flex: 1;
            min-height: 0 !important; /* 避免被默认撑高 */
            overflow-y: auto !important; /* 内容多时出现滚动 */
        }
        /* 给编辑器最终渲染区（.ck-content）里的 table、td、th 加 1px 实线边框 */
        .ck-content table,
        .ck-content th,
        .ck-content td {
            border: 1px solid #000000;
            border-collapse: collapse;
        }        
    </style>

</head>
<body>
    <div class="main-container">
        <!-- 左侧树状结构面板 -->
        <div class="tree-panel">
            <h2>数据资源</h2>
            <div id="jstree-container"></div>
        </div>

        <!-- Word编辑器部分 -->
        <div class="word-editor">
            <div id="editor-container">
                <div id="editor"></div>
            </div>
        </div>

        <!-- 控制面板部分 -->
        <div class="control-panel">
            <div class="control-panel-content">
                <div class="control-panel-inputs">
                    <h1>"电力看经济"研究咨询平台</h1>

                    <div class="form-group">
                        <label for="query">查询内容：</label>
                        <textarea id="query" rows="3" placeholder="输入您的查询内容"></textarea>
                    </div>

                    <div class="form-group">
                        <label for="model-select">模型选择：</label>
                        <select id="model-select" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box;">
                            <option value="V3模型">光明-671B-V3模型</option>
                            <option value="R1模型">光明-671B-R1模型(推理)</option>
                            <option value="72B模型">光明-72B-模型</option>
                        </select>
                    </div>

                    <div class="button-container">
                        <button id="clear-btn" style="width: 80px;">清空</button>
                        <button id="run-btn" style="width: 80px;">运行</button>
                    </div>

                    <div class="status"><span class="status-label">状态：</span><span id="status">空闲</span></div>
                </div>

                <div class="output" id="output"></div>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // 初始化树状结构
            $('#jstree-container').jstree({
                'core': {
                    'data': [
                        {
                            'text': '公司',
                            'children': [
                                {
                                    'text': '本部',
                                    'children': [
                                        {'text': '区域电网电量交换情况(公司本部)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '供用电综合情况(公司本部)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '电量平衡情况(公司本部)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '全社会用电分类情况(公司本部)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '分城市全社会用电分类情况(公司本部)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '电网负荷特性(公司本部)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '系统无功补偿设备情况(公司本部)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '分布式发电生产情况(公司本部)', 'icon': 'jstree-themeicon-custom'}
                                    ]
                                },
                                {
                                    'text': '杭州',
                                    'children': [
                                        {'text': '电量平衡情况表(公司-杭州)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '电网负荷特性表(公司-杭州)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '全社会用电分类情况表(公司-杭州)', 'icon': 'jstree-themeicon-custom'}
                                    ]
                                },
                                {
                                    'text': '宁波',
                                    'children': [
                                        {'text': '电量平衡情况表(公司-宁波)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '电网负荷特性表(公司-宁波)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '全社会用电分类情况表(公司-宁波)', 'icon': 'jstree-themeicon-custom'}
                                    ]
                                },
                                {
                                    'text': '温州',
                                    'children': [
                                        {'text': '电量平衡情况表(公司-温州)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '电网负荷特性表(公司-温州)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '全社会用电分类情况表(公司-温州)', 'icon': 'jstree-themeicon-custom'}
                                    ]
                                },
                                {
                                    'text': '绍兴',
                                    'children': [
                                        {'text': '电量平衡情况表(公司-绍兴)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '电网负荷特性表(公司-绍兴)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '全社会用电分类情况表(公司-绍兴)', 'icon': 'jstree-themeicon-custom'}
                                    ]
                                }
                            ]
                        },
                        {
                            'text': '政府',
                            'children': [
                                {
                                    'text': '浙江',
                                    'children': [
                                        {'text': '浙江省能源消费总量表(政府-浙江)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '浙江省GDP增长情况表(政府-浙江)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '浙江省产业结构变化表(政府-浙江)', 'icon': 'jstree-themeicon-custom'}
                                    ]
                                },
                                {
                                    'text': '杭州',
                                    'children': [
                                        {'text': '杭州市能源消费总量表(政府-杭州)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '杭州市GDP增长情况表(政府-杭州)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '杭州市产业结构变化表(政府-杭州)', 'icon': 'jstree-themeicon-custom'}
                                    ]
                                },
                                {
                                    'text': '宁波',
                                    'children': [
                                        {'text': '宁波市能源消费总量表(政府-宁波)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '宁波市GDP增长情况表(政府-宁波)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '宁波市产业结构变化表(政府-宁波)', 'icon': 'jstree-themeicon-custom'}
                                    ]
                                },
                                {
                                    'text': '温州',
                                    'children': [
                                        {'text': '温州市能源消费总量表(政府-温州)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '温州市GDP增长情况表(政府-温州)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '温州市产业结构变化表(政府-温州)', 'icon': 'jstree-themeicon-custom'}
                                    ]
                                },
                                {
                                    'text': '绍兴',
                                    'children': [
                                        {'text': '绍兴市能源消费总量表(政府-绍兴)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '绍兴市GDP增长情况表(政府-绍兴)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '绍兴市产业结构变化表(政府-绍兴)', 'icon': 'jstree-themeicon-custom'}
                                    ]
                                }
                            ]
                        },
                        {
                            'text': '其他',
                            'children': [
                                {
                                    'text': '社科院',
                                    'children': [
                                        {'text': '2024-中国交通年鉴(社科院)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '2024-中国会计年鉴(社科院)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '2024-中国农村统计年鉴(社科院)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '2024-中国劳动统计年鉴(社科院)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '2024-中国商务年鉴(社科院)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '2023-中国城市建设统计年鉴(社科院)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '2022-中国能源统计年鉴(社科院)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '2022-世界经济年鉴(社科院)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '2022-中国国有资产监督管理年鉴(社科院)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '2021-中国信息产业年鉴(社科院)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '2018-中国500强企业发展报告(社科院)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '2017-国家电网公司年鉴(社科院)', 'icon': 'jstree-themeicon-custom'}
                                    ]
                                },
                                {
                                    'text': '中电联',
                                    'children': [
                                        {'text': '电力行业统计调查制度调查表-目录表(中电联)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '向国家统计局报送的具体统计资料清单(中电联)', 'icon': 'jstree-themeicon-custom'},
                                        {'text': '向统计信息共享数据库提供的统计资料清单(中电联)', 'icon': 'jstree-themeicon-custom'}
                                    ]
                                }
                            ]
                        }
                    ]
                },
                'plugins': ['wholerow', 'state', 'checkbox'],
                'state': {
                    'key': 'jstree_demo'
                },
                'checkbox': {
                    'three_state': false,
                    'cascade': 'down'
                }
            });

            // 绑定树节点点击事件
            $('#jstree-container').on('select_node.jstree deselect_node.jstree', function(e, data) {
                // 获取所有选中的节点
                const selectedNodes = $('#jstree-container').jstree('get_selected');
                // 获取所有选中节点的文本，但只包含表格节点（有自定义图标的节点）
                const selectedTexts = selectedNodes.map(nodeId => {
                    const node = $('#jstree-container').jstree('get_node', nodeId);
                    // 只处理有自定义图标的节点（表格节点）
                    if (node.icon === 'jstree-themeicon-custom') {
                        return '@' + node.text;
                    }
                    return '';
                }).filter(text => text !== ''); // 过滤掉空字符串
                // 用空格连接所有选中的文本
                document.getElementById('query').value = selectedTexts.join(' ');
            });

            // 初始化 CKEditor5
            DecoupledEditor
                .create(document.querySelector('#editor'), {
                    toolbar: {
                        items: [
                            'undo', 'redo',
                            '|', 'heading',
                            '|', 'fontFamily', 'fontSize', 'fontColor', 'fontBackgroundColor',
                            '|', 'bold', 'italic', 'underline', 'strikethrough',
                            '|', 'alignment',
                            '|', 'numberedList', 'bulletedList',
                            '|', 'indent', 'outdent',
                            '|', 'link', 'blockQuote', 'insertTable', 'mediaEmbed'
                        ],
                        shouldNotGroupWhenFull: true
                    },
                    fontFamily: {
                        options: [
                            'default',
                            'Arial, Helvetica, sans-serif',
                            'Courier New, Courier, monospace',
                            'Georgia, serif',
                            'Lucida Sans Unicode, Lucida Grande, sans-serif',
                            'Tahoma, Geneva, sans-serif',
                            'Times New Roman, Times, serif',
                            'Trebuchet MS, Helvetica, sans-serif',
                            'Verdana, Geneva, sans-serif',
                            '宋体, SimSun',
                            '黑体, SimHei',
                            '微软雅黑, Microsoft YaHei',
                            '楷体, KaiTi',
                            '仿宋, FangSong'
                        ]
                    },
                    fontSize: {
                        options: [
                            9,
                            11,
                            12,
                            14,
                            16,
                            18,
                            20,
                            22,
                            24,
                            26,
                            28,
                            36,
                            42
                        ]
                    },
                    language: 'zh-cn'
                })
                .then(editor => {
                    const toolbarContainer = document.querySelector('#editor-container');
                    toolbarContainer.prepend(editor.ui.view.toolbar.element);
                    window.editor = editor;
                })
                .catch(error => {
                    console.error(error);
                });

            const runBtn = document.getElementById('run-btn');
            const clearBtn = document.getElementById('clear-btn');
            const outputEl = document.getElementById('output');
            const statusEl = document.getElementById('status');
            const queryEl = document.getElementById('query');
            const modelSelectEl = document.getElementById('model-select');

            let eventSource = null;

            // Clear button click handler
            clearBtn.addEventListener('click', function() {
                // Clear CKEditor content
                if (window.editor) {
                    window.editor.setData('');
                }
                // Clear output element
                outputEl.textContent = '';
                // Reset status
                statusEl.textContent = '空闲';
            });

            // Run SSE task
            runBtn.addEventListener('click', function() {
                // 禁用运行按钮
                runBtn.disabled = true;

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
                    query_text: queryEl.value,  // 添加query_text参数
                    model: modelSelectEl.value,  // 添加选中的模型值
                    tools: [],
                    base_url: 'https://api.deepseek.com/v1',  // 使用默认值
                    api_key: 'sk-c1d34a4f21e3413487bb4b2806f6c4b8'  // 使用默认值
                };

                console.log('-------------------已发送/api/start_agent_task请求...--------------------------');
                let start=0
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
                        // console.log("收到SSE数据:", event.data);
                        const data = JSON.parse(event.data);

                        if (data['[done]']) {
                            statusEl.textContent = '完成';
                            eventSource.close();
                            // 任务完成时启用运行按钮
                            runBtn.disabled = false;
                        } else if (data.message) {
                            // 处理字体
                            // console.log('--------------------text属性--------------------------')
                            // console.log(typeof data.message);
                            let obj = JSON.parse(data.message).data;
                            let text = obj.content
                            let alignment = obj.alignment
                            let is_heading = obj.is_heading
                            let font_name = obj.font
                            let font_size = obj.size
                            let font_color = obj.color
                            // console.log('obj: ', obj);
                            // console.log('text: ', text);
                            // console.log('alignment: ', alignment);
                            // console.log('font_name: ', font_name);
                            // console.log('font_size: ', font_size);
                            // console.log('font_color: ', font_color);
                            // console.log('-------------------/text属性--------------------------')
                            // 将消息追加到 CKEditor 内容末尾
                            if (window.editor) {
                                window.editor.model.change(writer => {
                                    const root = window.editor.model.document.getRoot();
                                    // 定位到内容末尾，以便追加
                                    const insertPosition = window.editor.model.createPositionAt(root, 'end');

                                    // --------------------用于测试---------------
                                    if (start==0) {
                                    }

                                    // 拆分行
                                    // const lines = data.message.split('\\n');
                                    // const lines = text.split(/\\r?\\n/);
                                    const lines = text.split(/\\r?\\n/).filter(line => line !== undefined);
                                    // 逐行插入
                                    // console.log('--------------lines-----------------')
                                    // console.log(lines)
                                    // console.log('-------------/lines-----------------')
                                    if ( text.includes('\\n') ) {
                                        console.log('--------------有换行-----------------')
                                        console.log(lines)
                                        console.log('length=',lines.length)
                                        for (let i = lines.length; i > 0; i--) {
                                            console.log('i=',i)
                                        }
                                        console.log('-------------/有换行-----------------')
                                    } 

                                    // ----------------------超级大坑：ckeditor的model.change里，为了方便撤销，所有操作的顺序是反的，所以要先插入'softBreak'、然后再插入'。'----------------------
                                    for (let i = lines.length-1; i >= 0; i--) {
                                        if (is_heading=='true') {
                                            console.log('--------------绘制red标题-----------------')
                                            // 创建一个新的段落
                                            const paragraph = writer.createElement('paragraph', {
                                                alignment: alignment  // 设置段落居中
                                            });

                                            // 创建文本节点，应用字体、大小和颜色属性
                                            const textNode = writer.createText(lines[i], {
                                                fontFamily: font_name,
                                                fontSize: font_size,
                                                fontColor: font_color
                                            });

                                            // 将文本节点添加到段落中
                                            writer.append(textNode, paragraph);

                                            // 将段落插入到文档中
                                            writer.insert(paragraph, insertPosition);  

                                            console.log('-------------/绘制red标题-----------------')
                                        }
                                        else {
                                            writer.insertText(lines[i], insertPosition);
                                            // if (i < lines.length - 1 && lines[i].trim() !== '') {
                                            if (i > 0 && lines.length>=2) {
                                                writer.insertElement('softBreak', insertPosition);

                                                // const paragraph = writer.createElement('paragraph');
                                                // // 创建文本节点，应用字体、大小和颜色属性
                                                // const textNode = writer.createText('\\n', {
                                                //     fontFamily: font_name,
                                                //     fontSize: font_size,
                                                //     fontColor: font_color
                                                // });
                                                // // 将文本节点添加到段落中
                                                // writer.append(textNode, paragraph);
                                                // // 将段落插入到文档中
                                                // writer.insert(paragraph, insertPosition); 
                                            }
                                        }
                                    }
                                    // ---------------------/超级大坑：ckeditor的model.change里，为了方便撤销，所有操作的顺序是反的，所以要先插入'softBreak'、然后再插入'。'----------------------
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
                            // 任务完成时启用运行按钮
                            runBtn.disabled = false;
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
                            // 任务完成时启用运行按钮
                            runBtn.disabled = false;
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

                    let tool_data_eventSource = new EventSource('/api/get_task_tool_client_data_sse_stream?task_id=' + encodeURIComponent(task_id_from_server));
                    console.log('创建tool data SSE连接成功.');
                    console.log('tool_data_eventSource: ', log_eventSource);

                    tool_data_eventSource.onmessage = function(event) {
                        console.log("收到tool data SSE数据:", event.data);
                        const data = JSON.parse(event.data);

                        if (data['[done]']) {
                            statusEl.textContent = '完成';
                            tool_data_eventSource.close();
                            // 任务完成时启用运行按钮
                            runBtn.disabled = false;
                        } else if (data.message) {
                            console.log('--------data.message---------')
                            console.log(typeof data.message);
                            obj = JSON.parse(data.message);
                            console.log(typeof data.message);

                            console.log(obj)
                            console.log(obj.type)
                            console.log(obj['type'])
                            console.log('-----------------------------')
                            if (obj.type=='table') {
                                // 在这里绘制一个3x4的表格，表格数据随意示意下
                                console.log('----------------------table data--------------------------------')
                                console.log(obj)
                                console.log('---------------------/table data--------------------------------')
                                if (window.editor) {
                                    // 先执行插入表格命令（这个命令会修改模型并尝试设置 selection，但不一定成功）
                                    // 假设 editor 是 CKEditor5 实例
                                    const tableString = obj.data.content
                                    console.log('----------------------table str content--------------------------------')
                                    console.log(tableString)
                                    console.log('---------------------/table str content--------------------------------')
                                    // 解析字符串为二维数组，每行以换行符分隔，每个单元格以制表符分隔
                                    function parseTableData(str) {
                                        return str.trim().split('\\n').map(line => {
                                            // 分割后去掉空字符串
                                            return line.split('\\t').map(cell => cell.trim()).filter(cell => cell);
                                        });
                                    }

                                    const table_data = parseTableData(tableString);
                                    console.log('----------------------parsed table str content--------------------------------')
                                    console.log(table_data)
                                    console.log('---------------------/parsed table str content--------------------------------')
                                    const rows = table_data.length
                                    const columns = Math.max(...table_data.map(row => row.length));

                                    // window.editor.execute('insertTable', { rows: rows, columns: columns });
                                    window.editor.model.change(writer => {
                                        const root = window.editor.model.document.getRoot();

                                        // 获取编辑器内容末尾的位置
                                        const insertPosition = writer.createPositionAt(root, 'end');

                                        // 插入表格
                                        const tableElement = writer.createElement('table');

                                        writer.insert(tableElement, insertPosition);

                                        // 创建指定行数和列数的表格
                                        for (let r = 0; r < rows; r++) {
                                            const tableRow = writer.createElement('tableRow');
                                            writer.append(tableRow, tableElement);

                                            for (let c = 0; c < columns; c++) {
                                                const tableCell = writer.createElement('tableCell');
                                                writer.append(tableCell, tableRow);

                                                const paragraph = writer.createElement('paragraph');
                                                writer.append(paragraph, tableCell);

                                                const text = table_data[r][c] || ''; // 安全获取内容
                                                writer.insertText(text, paragraph);
                                            }
                                        }

                                        // 表格插入完成后，在表格后插入一个段落，使光标移到表格后面
                                        const paragraphAfterTable = writer.createElement('paragraph');
                                        writer.insert(paragraphAfterTable, writer.createPositionAfter(tableElement));

                                        // 移动光标到表格后的段落，以便后续插入正常
                                        writer.setSelection(paragraphAfterTable, 'end');
                                    });


                                    // 在一个新的 model.change 事务中修改刚刚插入的表格内容
                                    window.editor.model.change(writer => {
                                        const root = window.editor.model.document.getRoot();

                                        // 尝试使用 selection 获取表格元素
                                        let tableElement = window.editor.model.document.selection.getSelectedElement();
                                        // 如果 selection 没有返回表格，则从根节点倒序查找
                                        if (!tableElement || tableElement.name !== 'table') {
                                            for (let i = root.childCount - 1; i >= 0; i--) {
                                                const element = root.getChild(i);
                                                if (element.is('element', 'table')) {
                                                    tableElement = element;
                                                    break;
                                                }
                                            }
                                        }

                                        // 如果依然没找到表格，则输出错误并返回
                                        if (!tableElement) {
                                            console.error('无法找到插入的表格元素');
                                            return;
                                        }
                                        console.log('tableElement:', tableElement);

                                        // 遍历表格行和单元格，插入文字
                                        for (let r = 0; r < tableElement.childCount; r++) {
                                            const row = tableElement.getChild(r);
                                            console.log('row:', r, row);

                                            for (let c = 0; c < row.childCount; c++) {
                                                const cell = row.getChild(c);
                                                console.log('cell:', c, cell);

                                                // 移除单元格中现有的所有子元素
                                                for (const child of Array.from(cell.getChildren())) {
                                                    writer.remove(child);
                                                }

                                                // 先创建一个段落并追加到单元格中
                                                const paragraph = writer.createElement('paragraph');
                                                writer.append(paragraph, cell);

                                                // 再向这个已经插入到文档的段落中插入文本
                                                // const text = `第${r + 1}行-第${c + 1}列`;
                                                const text = table_data[r][c]
                                                console.log('Inserting text:', text);
                                                writer.insertText(text, paragraph, 0);
                                            }
                                        }
                                    });                                    

                                }
                            }
                        }
                    };

                    tool_data_eventSource.onerror = function(error) {
                        console.error('tool data stream SSE错误:', error);
                        tool_data_eventSource.close();
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
