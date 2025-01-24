import copy, pprint
import re

import streamlit as st
import pandas as pd
# from streamlit_file_browser import st_file_browser

import config
from config import dred, dgreen, dblue, dcyan
from tools.llm.api_client import LLM_Client, Concurrent_LLMs, Async_LLM

from agent.tool_agent import Tool_Agent
from tools.t2i.api_client_comfy import Comfy, Work_Flow_Type

import time

import base64
from io import StringIO

from tools.qa.file_qa import files_qa

from tools.retriever.legacy_search import Bing_Searcher
from utils.decorator import timer

# from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
from streamlit import runtime
from streamlit.web.server.websocket_headers import _get_websocket_headers
from utils.extract import get_ajs_anonymous_id_from_cookie
import pickle

from tools.retriever.search_and_urls import get_urls_content_list, get_bing_search_result
from tools.retriever.search_and_urls import get_url_text

# from tools.retriever.urls import aget_url_text

from agent.tools.code_tool import Code_Tool
from agent.tools.energy_investment_plan_tool import Energy_Investment_Plan_Tool
from agent.tools.folder_tool import Folder_Tool
from agent.tools.search_tool import Search_Tool
from agent.tools.url_content_qa_tool import Url_Content_QA_Tool


# 包方式运行：python -m streamlit run gpu_server/llm_webui_streamlit_server.py --server.port 7860

# 配置(必须第一个调用)
st.set_page_config(
    initial_sidebar_state="collapsed",
    page_title="Life-Agent",
    layout="wide",
)






# # 全局变量
# server_status = {'name': 'jack', 'age': 23}
#
# # 设置页面配置
# # st.set_page_config(layout="wide")
#
# # 处理查询参数
# params = st.experimental_get_query_params()
# if "show_modal" in params and params["show_modal"][0] == "true":
#     st.session_state.show_modal = True
# else:
#     st.session_state.show_modal = False
#
# # CSS样式
# st.markdown("""
#     <style>
#     .modal {
#         display: none;
#         position: fixed;
#         z-index: 1;
#         padding-top: 100px;
#         left: 0;
#         top: 0;
#         width: 100%;
#         height: 100%;
#         overflow: auto;
#         background-color: rgb(0,0,0);
#         background-color: rgba(0,0,0,0.4);
#     }
#     .modal-content {
#         background-color: #fefefe;
#         margin: auto;
#         padding: 20px;
#         border: 1px solid #888;
#         width: 80%;
#     }
#     .close {
#         color: #aaa;
#         float: right;
#         font-size: 28px;
#         font-weight: bold;
#     }
#     .close:hover,
#     .close:focus {
#         color: black;
#         text-decoration: none;
#         cursor: pointer;
#     }
#     </style>
#     """, unsafe_allow_html=True)
#
# # JavaScript脚本
# st.markdown("""
#     <script>
#     function openModal() {
#         var modal = document.getElementById("myModal");
#         modal.style.display = "block";
#     }
#     function closeModal() {
#         var modal = document.getElementById("myModal");
#         modal.style.display = "none";
#         window.location.href = window.location.href.split('?')[0] + "?show_modal=false";
#     }
#     </script>
#     """, unsafe_allow_html=True)
#
# # 侧边栏按钮
# if st.sidebar.button('打开窗口'):
#     st.experimental_set_query_params(show_modal="true")
#     st.session_state.show_modal = True
#
# # 悬浮窗口的HTML结构
# if st.session_state.show_modal:
#     st.markdown(f"""
#         <div id="myModal" class="modal" style="display: block;">
#             <div class="modal-content">
#                 <span class="close" onclick="closeModal()">&times;</span>
#                 <h2>Server Status</h2>
#                 <p>Name: {server_status['name']}</p>
#                 <p>Age: {server_status['age']}</p>
#             </div>
#         </div>
#         """, unsafe_allow_html=True)
#
# # 主页面内容
# st.write("欢迎使用Streamlit悬浮窗口示例！")
#
# # JavaScript 用于刷新页面
# if st.session_state.show_modal:
#     st.markdown("""
#         <script>
#         openModal();
#         </script>
#         """, unsafe_allow_html=True)









# st.set_page_config(
#     page_title=None,
#     page_icon=None,
#     layout="centered",
#     initial_sidebar_state="auto",
#     menu_items=None
# )
@st.cache_resource  # cache_resource主要用于访问db connection等仅调用一次的全局资源
def llm_init():
    # 读取session的pickle数据
    # if 'session_data' not in st.session_state:
    #     st.session_state.session_data = load_pickle_on_startup()

    # # 所有LLM的url统一设置
    # if 'llm_api_1_url' in st.session_state:
    #     main_llm_url = st.session_state.main_llm_url
    # else:
    #     main_llm_url = config.Global.llm_url

    # LLM_Client.Set_All_LLM_Server(config.Global.llm_url)
    # LLM_Client.Set_All_LLM_Server('http://127.0.0.1:8001/v1/')
    # dgreen(f'初始化所有LLM的url_endpoint: ', end='', flush=True)
    # dblue(f'"{LLM_Client.Get_All_LLM_Server()}"')

    # 初始化 mem_llm
    mem_llm = LLM_Client(
        url=config.Domain.llm_url,
        api_key=config.Global.llm_key,
        model_id=config.Global.llm_model,
        history=True,  # 这里打开llm的history，对话历史与streamlit显示的内容区分开
        print_input=False,
    )
    draw_llm = LLM_Client(
        url=config.Domain.llm_url,
        api_key=config.Global.llm_key,
        model_id=config.Global.llm_model,
        history=False,  # 这里打开llm的history，对话历史与streamlit显示的内容区分开
        print_input=False,
    )
    # mem_llm = LLM_Client(
    #     history=history,  # 这里打开llm的history，对话历史与streamlit显示的内容区分开
    #     print_input=False,
    # )
    dgreen('初始化mem_llm完毕: ', end='', flush=True)
    # dblue(f'"history={history}, temperature(初始)={temperature}"')
    return mem_llm, draw_llm

def _get_session():
    from streamlit.runtime import get_instance
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    runtime = get_instance()
    session_id = get_script_run_ctx().session_id
    session_info = runtime._session_mgr.get_session_info(session_id)
    dred(session_id)
    dred(session_info)
    if session_info is None:
        raise RuntimeError("Couldn't get your Streamlit Session object.")
    return session_info.session

def get_session_id():
    # _get_session()
    # 获取session_id
    try:
        session_id = ''
        # session_context = get_script_run_ctx()
        # session_id = session_context.session_id
        # session_info = runtime.get_instance().get_client(session_id)
        # ip = session_info.request.remote_ip
        # # dgreen(f'session id: "{session_context}"')
        # dgreen(f'session id: "{session_id}"')
        # dgreen(f'session_info: "{session_info}"')
        # dgreen(f'request: "{session_info.request}"')
        # dgreen(f'ip: "{ip}"')

        cookie_str = _get_websocket_headers()['Cookie']
        # cookie_str = st.context.headers()['Cookie']

        ajs_anonymous_id = get_ajs_anonymous_id_from_cookie(cookie_str)
        # dred(f'ajs_anonymous_id: "{ajs_anonymous_id}"')

        st.session_state.session_data['sid'] = ajs_anonymous_id
        # st.session_state.sid = ajs_anonymous_id
    except Exception as e:
        dred(f'get anonymous_id failed: "{e}"')
        st.session_state.session_data['sid'] = ''

def load_pickle_on_refresh():
    get_session_id()
    sid = st.session_state.session_data['sid']
    # dgreen('开始加载会话信息...')
    dred(f'=============load_pickle_on_startup=========')
    dred(f'sid: "{sid}"')
    dred(f'============================================')

    session_data = None

    work_dir = config.Global.get_work_dir() # "/home/tutu/server/life-agent"
    # dred(f'work dir: "{work_dir}"')
    session_pkl_file = work_dir + f'/streamlit_session_{sid}.pkl'

    try:
        with open(session_pkl_file, "rb") as f:
            session_data = pickle.load(f)
        st.session_state.session_data = session_data
        # dred(f'读取了session_data数据: \n"{session_data}"')

        # 装载chat历史
        # st.session_state.messages = st.session_state.session_data['msgs']

    except Exception as e:
        # dred(f'读取default会话文件出错: "{e}"')
        dred('未找到会话文件，使用默认会话配置.')
        dred(f'------------会话配置------------')
        pprint.pprint(default_session_data)
        dred(f'------------------------------')
        st.session_state.session_data = default_session_data
        st.session_state.session_data['sid'] = sid

def save_pickle():
    # get_session_id()
    # dgreen(f'sd: \n{st.session_state}')
    sid = st.session_state.session_data['sid']

    work_dir = config.Global.get_work_dir() # "/home/tutu/server/life-agent"
    dred(f'WORK DIR saved is: "{work_dir}"')
    session_pkl_file = work_dir + f'/streamlit_session_{sid}.pkl'

    try:
        with open(session_pkl_file, "wb") as f:
            pickle.dump(st.session_state.session_data, f)
        # dred(f'存储了session_data数据: \n"{st.session_state.session_data}"')
        # dred(f'存储sid: "{sid}"')

    except Exception as e:
        dred(f'存储会话文件出错: "{e}"')

default_session_data = {
    'sid': '',
    'msgs': [],
    'paras': {
        # 'initial_sidebar_state':'collapsed',    # collapsed/auto

        'url_prompt': '',
        'multi_line_prompt': '',
        'is_agent': False,
        'latex': False,
        'connecting_internet': False,
        'use_think_model': False,
        'draw': False,


        'local_llm_temperature': 0.7,
        'local_llm_max_new_token': 4096,
        'concurrent_num': 3,

        'files': [],                            # file_uploader返回的UploadedFile列表
        'last_files_num_of_file_uploader':0,    # 用于判断是否是file_uploader将files删光，用于和files没有而会话历史有文件数据的情况
        'file_column_raw_data': {},             # 用于管理和显示会话内UploadedFile数据
        'system_prompt': config.Global.llm_system_prompt,
        'role_prompt': '',

        'main_llm_url': config.Domain.llm_url,
        'main_llm_key': config.Global.llm_key,
        'main_llm_model_id': config.Global.llm_model,

        # 'input_translate': False,

        # 'english_llm_url': config.Global.llm_url2,
        # 'english_llm_key': config.Global.llm_key2,
        # 'english_llm_model_id': config.Global.llm_model2,
    }
}


def session_state_init():
    # 状态的初始化

    # 注意
    # 第一级变量，可以用st.session_state.some_para1
    # 第二级变量，可以用st.session_state.some_para1['some_para2']

    if 'first_page_on_load' not in st.session_state:
        st.session_state['first_page_on_load'] = True

    if 'processing' not in st.session_state:
        # print('=================================状态初始化==================================')
        st.session_state['processing'] = False
        # print(f'st.session_state.processing = {st.session_state.processing}')
        
    # if 'messages' not in st.session_state:
    #     st.session_state['messages'] = []
        # print(f'st.session_state.messages = {st.session_state.messages}')

    if 'session_data' not in st.session_state:
        st.session_state['session_data'] = default_session_data

    if 'prompt' not in st.session_state:
        st.session_state['prompt'] = ''
        # print(f'st.session_state.prompt = "{st.session_state.prompt}"')
        # print('=============================================================================')
    
# 返回searcher及其loop
# 这里不能用@st.cache_resource，否则每次搜索结果都不变
# @st.cache_resource
def search_init(concurrent_num=3, in_stream_buf_callback=None):
    import sys
    fix_streamlit_in_win = True if sys.platform.startswith('win') else False
    return Bing_Searcher.create_searcher_and_loop(fix_streamlit_in_win, in_stream_buf_callback=in_stream_buf_callback, in_search_num=concurrent_num)   # 返回loop，主要是为了在searcher完成start后，在同一个loop中执行query_bing_and_get_results()

# asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
mem_llm, draw_llm = llm_init()

def async_llm_local_response_concurrently(in_st, in_prompt, in_role_prompt='', in_concurrent_num=3):
    cols = in_st.columns([1]*in_concurrent_num)
    async_llms = []
    i = 0
    for col in cols:
        i += 1
        suffix = ' ${}^{【local' + f'-{i}' + '】}$ \n\n'
        async_llm = Async_LLM()
        async_llms.append(async_llm)
        async_llm.init(
            col.empty().markdown, 
            # col.container(border=True).empty().markdown, 
            in_prompt, 
            in_role_prompt=in_role_prompt,
            in_extra_suffix=suffix,
            in_streamlit=True,
            in_temperature= st.session_state.session_data['paras']['local_llm_temperature'],
        )
        async_llm.start()
    return async_llms

def agent_init():
    pass

    # tools = [Search_Tool, Code_Tool, Energy_Investment_Plan_Tool, QA_Url_Content_Tool]
    # print(f'工具: [')
    # for tool in tools:
    #     print(tool.name + ', ')
    # print(f'] 已加载.')
    #
    # agent = Tool_Agent(
    #     in_query=prompt,
    #     in_tool_classes=tools,
    #     inout_status_list=status_data['status_list'],
    #     in_status_stream_buf=status.markdown,
    #     inout_output_list=final_answer_list,
    #     in_output_stream_buf=placeholder1.markdown,
    # )
    # agent.init()

# @timer
# def ask_llm(prompt, paras):
#     role_prompt = paras['role_prompt']
#     url_prompt = paras['url_prompt']
#     connecting_internet = paras['connecting_internet']
#     draw = paras['draw']
#     is_agent = paras['is_agent']
#     system_prompt = paras['system_prompt']
#     files = paras['files']
# # def llm_response_concurrently(prompt, role_prompt, connecting_internet, connecting_internet_detail, is_agent):
#     # =================================agent功能=================================
#     if draw:
#
#         answer = draw_llm.ask_prepare(
#             in_question=f'''
# 请将描述"{prompt}"转换为stable diffusion的英文的出图提示词，返回的提示词风格如下（注意必须全部为英文，且只返回引号内的内容）:
# "Energetic (puppy playing in a water fountain:1.5) in a (lively urban park:1.4), with (splashing water droplets:1.4) and (amused onlookers:1.3), intricate details, (vibrant blue and green tones:1.4), (joyful playful atmosphere:1.5), (bright sunny daylight:1.4), high-definition, sharp focus, perfect composition, (modern photography:1.5) (smartphone camera:1.5) (social media post:1.5)"
# ''',
#             in_temperature=st.session_state.session_data['paras']['local_llm_temperature'],
#             in_max_new_tokens=st.session_state.session_data['paras']['local_llm_max_new_token'],
#             in_system_prompt=system_prompt,
#         ).get_answer_and_sync_print()
#         place_holder = st.chat_message('assistant').empty()
#         place_holder.markdown(answer)
#
#         client = Comfy()
#         client.set_server_address('192.168.124.33:7869')
#         client.set_workflow_type(Work_Flow_Type.simple)
#         client.set_simple_work_flow(
#             positive=answer,
#             negative='low quality, low res, bad face, bad hands, ugly, bad fingers, bad legs, text, watermark',
#             # seed=seed,
#             ckpt_name='sdxl_lightning_2step.safetensors',
#             height=1024,
#             width=1024,
#             batch_size=2,
#         )
#         images = client.get_images()
#         rtn_images_data = {
#             'type':'pics',
#             'data':[]
#         }
#         one_image_data = {
#             'caption':'',
#             'data':None,
#         }
#
#         for node_id in images:
#             for image_data in images[node_id]:
#                 from PIL import Image
#                 import io
#                 image = Image.open(io.BytesIO(image_data))
#                 place_holder.image(image, caption=prompt, use_column_width=True)
#
#                 # 一张图的标题和data
#                 one_image_data['caption'] = prompt
#                 one_image_data['data'] = image
#
#                 # list添加新图
#                 rtn_images_data['data'].append(copy.deepcopy(one_image_data))
#
#                 # image.save(f'{self.temp_dir}/{self.client_id}_{i}.jpg')
#         # client.save_images_to_temp_dir()
#         return None, None, answer, rtn_images_data
#
#     if is_agent:
#         final_answer_list = []
#         status_data = {
#             'type':'status',
#             'title':'Agent',
#             'status_list':[],
#         }
#         status = st.status(label=":green[Agent]", expanded=True)
#         status.markdown('任务(ReAct模式)已启动...')
#
#         assistant = st.chat_message('assistant')
#         placeholder1 = assistant.empty()
#
#         # LLM_Client.Set_All_LLM_Server('http://116.62.63.204:8001/v1/')
#         tools = [Search_Tool, Code_Tool, Energy_Investment_Plan_Tool, QA_Url_Content_Tool]
#         print(f'工具: [')
#         for tool in tools:
#             print(tool.name+', ')
#         print(f'] 已加载.')
#         agent = Tool_Agent(
#             in_query=prompt,
#             in_tool_classes=tools,
#             inout_status_list=status_data['status_list'],
#             in_status_stream_buf=status.markdown,
#             inout_output_list=final_answer_list,
#             in_output_stream_buf=placeholder1.markdown,
#         )
#         agent.init()
#         success = agent.run()
#         print(f'final_answer_list: {final_answer_list}')
#         status_list = status_data["status_list"]
#         print(f'status_list: {status_list}')
#
#         status.update(label=f":green[Agent已完成任务]", state='complete', expanded=True)
#         return status_data, None, '\n'.join(final_answer_list), None
#     # if is_agent:
#     #     final_answer = ''
#     #     status_data = {
#     #         'type':'status',
#     #         'title':'调用Agent',
#     #         'status_list':[],
#     #     }
#     #     status = st.status(label=":green[Agent已启动...]", expanded=True)
#     #
#     #     assistant = st.chat_message('assistant')
#     #     placeholder1 = assistant.empty()
#     #
#     #     status_data['status_list'].append("搜索引擎bing.com调用中...")
#     #     status.markdown(status_data['status_list'][-1])
#     #     searcher = search_init(concurrent_num=st.session_state.concurrent_num, in_stream_buf_callback=placeholder1.markdown)
#     #
#     #     # flicker1 = Flicker_Task(in_stream_buf_callback=placeholder1.markdown)
#     #     # flicker1.init(in_streamlit=True).start()
#     #     status_data['status_list'].append("搜索结果已返回, 尝试解读中...")
#     #     status.markdown(status_data['status_list'][-1])
#     #     gen = searcher.search_and_ask_yield(prompt, in_max_new_tokens=1024)
#     #     status_data['status_list'].append("搜索引擎bing.com调用中...")
#     #     status.markdown(status_data['status_list'][-1])
#     #     for res in gen:
#     #         chunk = res['response']
#     #         if res['response_type']=='debug':
#     #             status_data['status_list'].append(chunk)
#     #             status.markdown(status_data['status_list'][-1])
#     #         elif res['response_type']=='final':
#     #             final_answer += chunk
#     #             placeholder1.markdown(final_answer)
#     #         # placeholder1.markdown(final_answer + flicker1.get_flicker())
#     #     # flicker1.set_stop()
#     #     status.update(label=f":green[Agent调用完毕]", state='complete', expanded=True)
#     #     return status_data, None, final_answer, None
#     # =================================搜索并llm=================================
#     if connecting_internet:
#         # =================================搜索=================================
#         status = st.status(label=":green[启动联网解读任务...]", expanded=False)
#         status.markdown("搜索引擎bing.com调用中...")
#         assistant = st.chat_message('assistant')
#
#         # if not connecting_internet_detail:
#         #     # 不包含明细的联网搜索和解读
#         #     placeholder1 = assistant.empty()
#         #     # searcher = search_init(concurrent_num=st.session_state.concurrent_num)
#         #     # print(f'********1 placeholder.markdown: {placeholder.markdown}')
#         #     searcher = search_init(concurrent_num=st.session_state.concurrent_num, in_stream_buf_callback=assistant.empty().markdown)
#         #     rtn, search_urls = searcher.legacy_search_and_ask(prompt)
#         #
#         #     final_answer = ''
#         #     placeholder2 = assistant.empty()
#         #     # print(f'********2 placeholder.markdown: {placeholder.markdown}')
#         #     for chunk in rtn.get_answer_generator():
#         #         final_answer += chunk
#         #         placeholder2.markdown(final_answer + searcher.flicker.get_flicker())
#         #     placeholder2.markdown('\n\n')
#         #     final_answer += '\n\n'
#         #     i = 0
#         #     print(f'-------------------------------{search_urls}+++++++++++++')
#         #     for search_url in search_urls:
#         #         i += 1
#         #         url_md = f'[{search_url[:30]}...]({search_url} "{search_url}")'
#         #         url_string = f'【{i}】{url_md} \n\n'
#         #         final_answer += url_string
#         #         placeholder2.markdown(url_string)
#         #
#         #     return None, None, final_answer, None
#
#         searcher = search_init(concurrent_num=st.session_state.session_data['paras']['concurrent_num'])
#
#         async_llms = async_llm_local_response_concurrently(
#             in_st=assistant,
#             in_prompt=prompt,
#             in_role_prompt=role_prompt,
#             in_concurrent_num=st.session_state.session_data['paras']['concurrent_num'],
#         )
#         # 非联网llm调用，用于和联网llm解读结果对比
#         #async_llm = Async_LLM()
#         #async_llm.init(
#         #    assistant.empty().markdown,
#         #    prompt,
#         #    in_role_prompt=role_prompt,
#         #    in_extra_suffix=' ${}^{【local】}$ \n\n',
#         #    in_streamlit=True
#         #)
#         #async_llm.start()
#
#         internet_search_result = searcher.search(prompt)
#         # print(f'internet_search_result: {internet_search_result}')
#         status.markdown("搜索引擎bing.com调用完毕.")
#
#         # 为调用Concurrent_LLMs准备输入参数
#         num = len(internet_search_result)
#         prompts = [prompt]*(num)    # 所有的question
#         suffixes = []
#         contents = []
#         callbacks = []
#
#         # 显示非联网的解读结果stream[0]作为参考、以及所有联网解读结果stream[k]
#         # assistant = st.chat_message('assistant')
#         first_placeholder = None
#         for i in range(num):
#             # 所有需要理解的文本（需要嵌入question）
#             content = '\n'.join(internet_search_result[i][1])
#             contents.append(content)
#             # 所有llm的stream输出用的bufs，注意这里需要在st.chat_message('assistant')下生成stream
#             placeholder = assistant.empty()
#             if i==0:
#                 first_placeholder = placeholder
#             callbacks.append(placeholder.markdown)
#
#             url = internet_search_result[i][0]
#             url_md = f'[{url[:30]}...]({url} "{url}") \n\n'
#             index = f'【{i+1}】'
#             suffix = '\n\n${}^{' + index + '}$' + url_md + '\n\n'    # 用markdown格式显示[1]为上标
#             suffixes.append(suffix)
#         # 用于显示临时信息，vllm全速输出时，会覆盖这个临时信息
#         # first_placeholder.markdown('解读结果即将返回...')
#
#         # 初始化Concurrent_LLMs并运行输出status
#         llms = Concurrent_LLMs()
#         llms.init(prompts, contents, callbacks, in_extra_suffixes=suffixes)
#         for task_status in llms.start_and_get_status():
#             status.update(label=f":green[{task_status['describe']}]", state=task_status['type'], expanded=False)
#             status.markdown(task_status['detail'])
#
#
#         for llm in async_llms:
#             llm.wait()
#
#         # 将完整的输出结果，返回
#         final_answer = ''
#         # final_answer += async_llm.final_response
#         for answer in task_status['llms_full_responses']:
#             # 这里task_status是llms.start_and_get_status()结束后的最终状态
#             final_answer += answer
#         return None, async_llms, final_answer, None
#     else:
#         # =================================local llm=================================
#         all_prompt = role_prompt
#         mem_llm.set_role_prompt(all_prompt)
#
#         if url_prompt:
#             # 如果填了url
#             searcher = Bing_Searcher.create_searcher_and_loop()
#             result = searcher.loop.run_until_complete(searcher.get_url_content(in_url=url_prompt))
#             # result = await quick_get_url_text(url_prompt)
#             all_prompt = f'请严格根据URL(网页链接)返回的内容回答问题, URL(网页链接)返回的具体内容为: \n#############################################\n"{result}"\n#############################################\n'
#             mem_llm.set_role_prompt(all_prompt)
#
#         files_info_dict = st.session_state.session_data['paras']['file_column_raw_data']
#         if 'file_content' in files_info_dict:
#             # result = StringIO(f.getvalue().decode("utf-8")).read()
#             result = files_info_dict['file_content'][0]
#             dred(f'===========file_content===========\n"{result}"')
#             fname = files_info_dict['file_name'][0]
#             all_prompt = f'请严格根据文件({fname})返回的内容回答问题, 文件返回的具体内容为: "{result}"'
#             mem_llm.set_role_prompt(all_prompt)
#
#             # ans = mem_llm.ask_prepare(
#             #     in_question='文件目录返回给我',
#             #     in_temperature=st.session_state.local_llm_temperature,
#             #     in_max_new_tokens=st.session_state.local_llm_max_new_token,
#             #     in_system_prompt=system_prompt,
#             # ).get_answer_and_sync_print()
#             # st.markdown(ans)
#
#         place_holder = st.chat_message('assistant').empty()
#         full_res = ''
#
#         # 如果需要将query翻译为英文，并调用擅长英语的模型
#         # if st.session_state.session_data['paras']['input_translate']:
#         #     translate_llm = LLM_Client(
#         #         history=False,
#         #         url=st.session_state.session_data['paras']['main_llm_url'],
#         #         print_input=False,
#         #     )
#         #
#         #     dblue(f'需翻译的输入: "{prompt}"')
#         #     # translate_llm.set_role_prompt('不管输入是什么，你都不会对输入的内容进行解读，都直接将输入翻译为英文，且绝对不增加额外的引号')
#         #     translated_input = translate_llm.ask_prepare(
#         #         in_question=f'将"{prompt}"翻译为英文，不要增加额外的引号',
#         #         in_temperature = st.session_state.session_data['paras']['local_llm_temperature'],
#         #         in_max_new_tokens=st.session_state.session_data['paras']['local_llm_max_new_token'],
#         #         in_system_prompt = '你擅长将中文翻译为英语'
#         #     ).get_answer_and_sync_print()
#         #     dblue(f'翻译后的输入: "{translated_input}"')
#         #
#         #     prompt = translated_input
#         #
#         #     mem_llm.refresh_endpoint(
#         #         st.session_state.session_data['paras']['english_llm_url'],
#         #         st.session_state.session_data['paras']['english_llm_key'],
#         #         st.session_state.session_data['paras']['english_llm_model_id'],
#         #     )
#
#
#         # llm输出、统计输出时间
#         start_time1 = time.time()
#
#         gen = mem_llm.ask_prepare(
#             in_question=prompt,
#             in_temperature=st.session_state.session_data['paras']['local_llm_temperature'],
#             in_max_new_tokens=st.session_state.session_data['paras']['local_llm_max_new_token'],
#             in_system_prompt=system_prompt,
#         ).get_answer_generator()
#
#
#         wait_first_token = True
#         for res in gen:
#             if res and wait_first_token:
#                 start_time2 = time.time()
#                 wait_first_token = False
#
#             full_res += res
#             place_holder.markdown(full_res)
#
#         if wait_first_token:
#             # 可能输出为空，则这里要开始计时
#             start_time2 = time.time()
#
#         p_tokens = mem_llm.get_prompt_tokens()
#         c_tokens = mem_llm.get_completion_tokens()
#         all_tokens = p_tokens+c_tokens
#
#         end_time = time.time()
#         input_time = start_time2 - start_time1
#         output_time = end_time - start_time2
#         input_time_str = f'{input_time:.1f}'
#         output_time_str = f'{output_time:.1f}'
#         all_time_str = f'{input_time+output_time:.1f}'
#
#         try:
#             input_ts_str = f'{p_tokens/input_time:.1f}'
#             output_ts_str = f'{c_tokens/output_time:.1f}'
#
#             # 显示: 输入、输出token，首字时间、输出时间，首字前t/s、输出t/s
#             # 10445 ( 10039 + 406 ) tokens in 31.6 ( 10.6 + 21.0 ) secs, 946.3 t/s, 19.3 t/s
#             full_res += f'\n\n:green[{all_tokens} ( {p_tokens} + {c_tokens} ) tokens in {all_time_str} ( {input_time_str} + {output_time_str} ) secs, {input_ts_str} t/s, {output_ts_str} t/s ]'
#             # full_res += f'\n\n:green[( {p_tokens}输入 + {c_tokens}输出 = {p_tokens+c_tokens} tokens )]'
#         except Exception as e:
#             dred(f'统计时间为0.')
#
#
#         place_holder.markdown(full_res)
#         # dred(f'full_res: {full_res}')
#         return None, None, full_res, None

def show_string_container_latex(streamlit, s):
    """
    处理输入字符串，识别 LaTeX 表达式并使用 Streamlit 渲染。

    Args:
        s (str): 输入的字符串，包含 LaTeX 表达式。
    """
    # 正则表达式模式，匹配 \[ ... \] 或 \( ... \)
    pattern = r'\\\[(.*?)\\\]|\\\((.*?)\\\)'

    # 上一次匹配结束的位置
    last_index = 0

    # 遍历所有匹配的 LaTeX 表达式
    for match in re.finditer(pattern, s):
        start, end = match.span()

        # 提取 LaTeX 表达式前的普通文本并渲染为 Markdown
        if start > last_index:
            markdown_text = s[last_index:start]
            streamlit.markdown(markdown_text)

        # 提取 LaTeX 表达式内容
        latex_content = match.group(1) if match.group(1) else match.group(2)
        streamlit.latex(latex_content)

        # 更新最后处理的位置
        last_index = end

    # 处理最后一个 LaTeX 表达式后的文本
    if last_index < len(s):
        markdown_text = s[last_index:]
        streamlit.markdown(markdown_text)

def ask_llm(prompt, paras):
    role_prompt = paras['role_prompt']
    url_prompt = paras['url_prompt']
    connecting_internet = paras['connecting_internet']
    use_think_model = paras['use_think_model']
    draw = paras['draw']
    is_agent = paras['is_agent']
    using_latex = paras['latex']
    system_prompt = paras['system_prompt']
    files = paras['files']
# def llm_response_concurrently(prompt, role_prompt, connecting_internet, connecting_internet_detail, is_agent):
    # =================================agent功能=================================
    if draw:

        answer = draw_llm.ask_prepare(
            question=f'''
请将描述"{prompt}"转换为stable diffusion的英文的出图提示词，返回的提示词风格如下（注意必须全部为英文，且只返回引号内的内容）:
"Energetic (puppy playing in a water fountain:1.5) in a (lively urban park:1.4), with (splashing water droplets:1.4) and (amused onlookers:1.3), intricate details, (vibrant blue and green tones:1.4), (joyful playful atmosphere:1.5), (bright sunny daylight:1.4), high-definition, sharp focus, perfect composition, (modern photography:1.5) (smartphone camera:1.5) (social media post:1.5)"
''',
            temperature=st.session_state.session_data['paras']['local_llm_temperature'],
            max_new_tokens=st.session_state.session_data['paras']['local_llm_max_new_token'],
            system_prompt=system_prompt,
        ).get_answer_and_sync_print()
        place_holder = st.chat_message('assistant').empty()
        place_holder.markdown(answer)

        client = Comfy()
        client.set_server_address('192.168.124.33:7869')
        client.set_workflow_type(Work_Flow_Type.simple)
        client.set_simple_work_flow(
            positive=answer,
            negative='low quality, low res, bad face, bad hands, ugly, bad fingers, bad legs, text, watermark',
            # seed=seed,
            ckpt_name='sdxl_lightning_2step.safetensors',
            height=1024,
            width=1024,
            batch_size=2,
        )
        images = client.get_images()
        rtn_images_data = {
            'type':'pics',
            'data':[]
        }
        one_image_data = {
            'caption':'',
            'data':None,
        }

        for node_id in images:
            for image_data in images[node_id]:
                from PIL import Image
                import io
                image = Image.open(io.BytesIO(image_data))
                place_holder.image(image, caption=prompt, use_column_width=True)

                # 一张图的标题和data
                one_image_data['caption'] = prompt
                one_image_data['data'] = image

                # list添加新图
                rtn_images_data['data'].append(copy.deepcopy(one_image_data))

                # image.save(f'{self.temp_dir}/{self.client_id}_{i}.jpg')
        # client.save_images_to_temp_dir()
        return None, None, answer, rtn_images_data

    if is_agent:
        final_answer_list = []
        status_data = {
            'type':'status',
            'title':'Agent',
            'status_list':[],
        }
        status = st.status(label=":green[Agent]", expanded=True)
        status.markdown('任务(ReAct模式)已启动...')


        assistant = st.chat_message('assistant')
        placeholder1 = assistant.empty()

        # LLM_Client.Set_All_LLM_Server('http://116.62.63.204:8001/v1/')
        tools = [Search_Tool, Code_Tool, Energy_Investment_Plan_Tool, Url_Content_QA_Tool]
        print(f'工具: [')
        for tool in tools:
            print(tool.name+', ')
        print(f'] 已加载.')
        agent = Tool_Agent(
            in_query=prompt,
            in_tool_classes=tools,
            inout_status_list=status_data['status_list'],
            in_status_stream_buf=status.markdown,
            inout_output_list=final_answer_list,
            in_output_stream_use_chunk=False,
            in_output_stream_buf=placeholder1.markdown,
        )
        agent.init()
        success = agent.run()
        print(f'final_answer_list: {final_answer_list}')
        status_list = status_data["status_list"]
        print(f'status_list: {status_list}')

        status.update(label=f":green[Agent已完成任务]", state='complete', expanded=True)
        return status_data, None, '\n'.join(final_answer_list), None
    # if is_agent:
    #     final_answer = ''
    #     status_data = {
    #         'type':'status',
    #         'title':'调用Agent',
    #         'status_list':[],
    #     }
    #     status = st.status(label=":green[Agent已启动...]", expanded=True)
    #
    #     assistant = st.chat_message('assistant')
    #     placeholder1 = assistant.empty()
    #
    #     status_data['status_list'].append("搜索引擎bing.com调用中...")
    #     status.markdown(status_data['status_list'][-1])
    #     searcher = search_init(concurrent_num=st.session_state.concurrent_num, in_stream_buf_callback=placeholder1.markdown)
    #
    #     # flicker1 = Flicker_Task(in_stream_buf_callback=placeholder1.markdown)
    #     # flicker1.init(in_streamlit=True).start()
    #     status_data['status_list'].append("搜索结果已返回, 尝试解读中...")
    #     status.markdown(status_data['status_list'][-1])
    #     gen = searcher.search_and_ask_yield(prompt, in_max_new_tokens=1024)
    #     status_data['status_list'].append("搜索引擎bing.com调用中...")
    #     status.markdown(status_data['status_list'][-1])
    #     for res in gen:
    #         chunk = res['response']
    #         if res['response_type']=='debug':
    #             status_data['status_list'].append(chunk)
    #             status.markdown(status_data['status_list'][-1])
    #         elif res['response_type']=='final':
    #             final_answer += chunk
    #             placeholder1.markdown(final_answer)
    #         # placeholder1.markdown(final_answer + flicker1.get_flicker())
    #     # flicker1.set_stop()
    #     status.update(label=f":green[Agent调用完毕]", state='complete', expanded=True)
    #     return status_data, None, final_answer, None
    # =================================搜索并llm=================================
    if connecting_internet:
        place_holder = st.chat_message('assistant').empty()
        # 初始化Concurrent_LLMs并运行输出status
        results = get_bing_search_result(query=prompt, use_proxy=True, result_num=3)
        for item in results:
            place_holder.markdown(item['url'])
        urls = [item['url'] for item in results]
        print(f'urls: {urls}')
        res_list = get_urls_content_list(urls=urls, res_type_list=['image', 'video'], use_proxy=True)
        print(f'res_list: {res_list}')
        res = []
        for k, v in res_list.items():
            for item in v:
                if item['type']=='image':
                    # place_holder.image(item['content'])
                    res.append({'type':'image', 'url':item['content']})
                elif item['type']=='video':
                    # place_holder.video(item['content'])
                    res.append({'type': 'video', 'url': item['content']})
        return None, None, None, res
    else:
        # =================================local llm=================================
        all_prompt = role_prompt
        mem_llm.set_role_prompt(all_prompt)

        if url_prompt:
            # 如果填了url
            # searcher = Bing_Searcher.create_searcher_and_loop()
            # result = searcher.loop.run_until_complete(searcher.get_url_content(in_url=url_prompt))
            result = get_url_text(url_prompt, use_proxy=False)
            dred(f'----------------get content from url----------------')
            dred(f'[url]: {url_prompt}')
            dred(f'[content]: {result}')
            dred(f'----------------------------------------------------')
            # result = get_url_text(url_prompt, use_proxy=False, raw_text=False, one_new_line=True)


            # result = await quick_get_url_text(url_prompt)
            all_prompt = f'请严格根据URL(网页链接)返回的内容回答问题, URL(网页链接)返回的具体内容为: \n#############################################\n"{result}"\n#############################################\n'
            mem_llm.set_role_prompt(all_prompt)

        files_info_dict = st.session_state.session_data['paras']['file_column_raw_data']
        if 'file_content' in files_info_dict:
            # result = StringIO(f.getvalue().decode("utf-8")).read()
            result = files_info_dict['file_content'][0]
            dred(f'===========file_content===========\n"{result}"')
            fname = files_info_dict['file_name'][0]

            print(f'type: {files_info_dict["file_type"][0]}')
            if not 'image' in files_info_dict["file_type"][0]:
                # 如果不是图片，即文本，将内容导入prompt
                all_prompt = f'请严格根据文件({fname})返回的内容回答问题, 文件返回的具体内容为: "{result}"'
                mem_llm.set_role_prompt(all_prompt)

            # ans = mem_llm.ask_prepare(
            #     in_question='文件目录返回给我',
            #     in_temperature=st.session_state.local_llm_temperature,
            #     in_max_new_tokens=st.session_state.local_llm_max_new_token,
            #     in_system_prompt=system_prompt,
            # ).get_answer_and_sync_print()
            # st.markdown(ans)

        # 新建think的输出框
        think_placeholder = None
        think_status = None

        if use_think_model:
            think_status = st.status(label=":green[思考]", expanded=True)
            think_placeholder = think_status.empty()

        # 新建result的输出框
        place_holder = st.chat_message('assistant').empty()
        full_res = {}
        if using_latex:
            full_res['type'] = 'latex'
        else:
            full_res['type'] = 'text'

        full_res['content'] = ''

        # 如果需要将query翻译为英文，并调用擅长英语的模型
        # if st.session_state.session_data['paras']['input_translate']:
        #     translate_llm = LLM_Client(
        #         history=False,
        #         url=st.session_state.session_data['paras']['main_llm_url'],
        #         print_input=False,
        #     )
        #
        #     dblue(f'需翻译的输入: "{prompt}"')
        #     # translate_llm.set_role_prompt('不管输入是什么，你都不会对输入的内容进行解读，都直接将输入翻译为英文，且绝对不增加额外的引号')
        #     translated_input = translate_llm.ask_prepare(
        #         in_question=f'将"{prompt}"翻译为英文，不要增加额外的引号',
        #         in_temperature = st.session_state.session_data['paras']['local_llm_temperature'],
        #         in_max_new_tokens=st.session_state.session_data['paras']['local_llm_max_new_token'],
        #         in_system_prompt = '你擅长将中文翻译为英语'
        #     ).get_answer_and_sync_print()
        #     dblue(f'翻译后的输入: "{translated_input}"')
        #
        #     prompt = translated_input
        #
        #     mem_llm.refresh_endpoint(
        #         st.session_state.session_data['paras']['english_llm_url'],
        #         st.session_state.session_data['paras']['english_llm_key'],
        #         st.session_state.session_data['paras']['english_llm_model_id'],
        #     )


        # llm输出、统计输出时间
        start_time1 = time.time()

        image_url = None
        if 'file_column_raw_data' in paras and 'file_content' in paras['file_column_raw_data']:
            image_url = paras['file_column_raw_data']["file_content"][0]

        print(f'image_url: "{image_url}"')
        gen = mem_llm.ask_prepare(
            question=prompt,
            image_url=image_url,
            temperature=st.session_state.session_data['paras']['local_llm_temperature'],
            max_new_tokens=st.session_state.session_data['paras']['local_llm_max_new_token'],
            system_prompt=system_prompt,
            remove_content_in_think_pairs=use_think_model,
        ).get_answer_generator()


        wait_first_token = True
        dred(f'-----------use_think_model: ({use_think_model})----------')

        think_content = ''
        think_status_data = {
            'type':'status',
            'title':'思考',
            'status_list':[],
        }

        think_chunk = ''
        result_chunk = ''

        all_content = ''
        result_content = ''
        for res in gen:
            all_content += res[0]   # 完整的、带<think>的输出，用于调试
            result_content += res[2]   # 完整的、带<think>的输出，用于调试
            if use_think_model:
                # think模型
                if res[0] and wait_first_token:
                    start_time2 = time.time()
                    wait_first_token = False

                result_chunk = res[2]
                full_res['content'] += result_chunk

                think_chunk = res[1]
                think_content += think_chunk
                think_placeholder.markdown(think_content)

                if (not think_chunk) and result_chunk:
                    # 开始result的输出
                    think_status.update(label=f":green[思考完毕]", state='complete', expanded=False)

            else:
                # 普通模型
                if res and wait_first_token:
                    start_time2 = time.time()
                    wait_first_token = False

                full_res['content'] += res

            full_res['content'] = full_res['content'].replace(r"\(", '').replace(r"\)", '').replace(r"\[", '').replace(r"\]", '')
            if using_latex:
                place_holder.latex(full_res['content'])
                # show_string_container_latex(place_holder, full_res['content'])
            else:
                place_holder.markdown(full_res['content'])

        if use_think_model:
            think_status_data['status_list'].append(think_content)
            think_status_data['title'] = '思考完毕'
            # think_status.update(label=f":green[思考完毕]", state='complete', expanded=True)

        if wait_first_token:
            # 可能输出为空，则这里要开始计时
            start_time2 = time.time()

        p_tokens = mem_llm.get_prompt_tokens()
        c_tokens = mem_llm.get_completion_tokens()
        all_tokens = p_tokens+c_tokens

        end_time = time.time()
        input_time = start_time2 - start_time1
        output_time = end_time - start_time2
        input_time_str = f'{input_time:.1f}'
        output_time_str = f'{output_time:.1f}'
        all_time_str = f'{input_time+output_time:.1f}'

        try:
            input_ts_str = f'{p_tokens/input_time:.1f}'
            output_ts_str = f'{c_tokens/output_time:.1f}'

            # 显示: 输入、输出token，首字时间、输出时间，首字前t/s、输出t/s
            # 10445 ( 10039 + 406 ) tokens in 31.6 ( 10.6 + 21.0 ) secs, 946.3 t/s, 19.3 t/s
            full_res['content'] += f'\n\n:green[{all_tokens} ( {p_tokens} + {c_tokens} ) tokens in {all_time_str} ( {input_time_str} + {output_time_str} ) secs, {input_ts_str} t/s, {output_ts_str} t/s ]'
            # full_res['content'] += f'\n\n:green[( {p_tokens}输入 + {c_tokens}输出 = {p_tokens+c_tokens} tokens )]'
        except Exception as e:
            dred(f'统计时间为0.')

        if using_latex:
            str = full_res['content'].replace(r"\(", '').replace(r"\)", '').replace(r"\[", '').replace(r"\]", '')
            # print(f'---------------------------------')
            # print(str)
            place_holder.latex(full_res['content'])
            # show_string_container_latex(place_holder, full_res['content'])
        else:
            place_holder.markdown(full_res['content'])
        # dred(f'full_res: {full_res['content']}')

        # str = full_res['content'].replace(r"\(", '').replace(r"\)", '').replace(r"\[", '').replace(r"\]", '')
        print(f'================all_content===================')
        print(all_content)
        print(f'================result_content===================')
        print(result_content)
        print(f'================full_res[\'content\']===================')
        print(full_res['content'])

        if use_think_model:
            return think_status_data, None, full_res, None
        else:
            return None, None, full_res, None

def on_clear_history():
    # st.session_state.messages = []
    st.session_state.session_data['msgs'] = []
    save_pickle()
    mem_llm.delete_history()
    dred('-----------on_clear_history--------------')

def on_cancel_response():
    mem_llm.cancel_response()
    st.session_state.processing = False
    st.session_state.prompt = ''

def on_chat_input_submit(in_prompt=None):
    st.session_state.processing = True
    if in_prompt:
        print(f'on_chat_input_submit invoked with prompt: {in_prompt}')
        st.session_state.prompt = in_prompt

def on_refresh():
    pass
    # print('=================================状态刷新==================================')
    # print(f'st.session_state.processing = {st.session_state.processing}')
    # print('============================================================================')

def st_display_pdf(pdf_file):
    with open(pdf_file, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="800" height="1000" type="application/pdf">'
    st.markdown(pdf_display, unsafe_allow_html=True)

# 将file_uploader或pickle文件的files转为data_editor显示
def refresh_file_column(in_widget, in_files, file_uploader_changed=False):
    df_files_info = None
    dblue(f'----------------------in_files----------------------------\n')
    dblue(in_files)
    dblue(f'---------------file_uploader_changed----------------------\n')
    dblue(file_uploader_changed)
    dblue(f'----------------------------------------------------------\n')

    if in_files is not None:
        # file_uploaders有输入时
        if len(in_files) > 0:
            # dred('============== >0 ====================')
            # 由于file_uploader操作造成的更新

            import base64
            file_column_raw_data = {
                "file_name": [f.name for f in in_files],  # string
                "file_type":[f.type for f in in_files],
                "file_selected": [True for f in in_files],  # bool
                "file_content": ["data:{mime_type};base64,{base64_string}".format(mime_type=f.type, base64_string=base64.b64encode(f.read()).decode("utf-8")) for f in in_files],    # string of file content
            }
            # # 文本文件
            # file_column_raw_data = {
            #     "file_name": [f.name for f in in_files],                                            # string
            #     "file_selected": [True for f in in_files],                                          # bool
            #     "file_content":[StringIO(f.getvalue().decode("utf-8")).read() for f in in_files],   # string of file content
            # }
            df_files_info = pd.DataFrame(file_column_raw_data)

            for f in in_files:
                dgreen(f'读取"{f.name}"成功.')
                print(f)

            # 存储session数据
            st.session_state.session_data['paras']['file_column_raw_data'] = file_column_raw_data
            st.session_state.session_data['paras']['last_files_num_of_file_uploader'] = len(in_files)
            save_pickle()
        elif len(in_files) == 0:
            if st.session_state['first_page_on_load'] == True:
                # 页面加载
                df_files_info = pd.DataFrame(st.session_state.session_data['paras']['file_column_raw_data'])
                st.session_state.session_data['paras']['last_files_num_of_file_uploader'] = 0   # 这里必须设置为0，因为file_uploader在页面刷新时肯定没有files
                save_pickle()
            else:
                if st.session_state.session_data['paras']['last_files_num_of_file_uploader'] > 0:
                    # 是因为file_uploader的操作，将files都删除了
                    df_files_info = None
                    on_clear_files()
                    st.session_state.session_data['paras']['last_files_num_of_file_uploader'] = 0
                    save_pickle()
                else:
                    # 其他控件的任何操作
                    pass

        return df_files_info

    # files信息：显示file_name和file_selected，不显示file_content
    # file_column_return_data = in_widget.data_editor(
    #     df_files_info,
    #     column_config={
    #         "file_name": st.column_config.TextColumn(
    #             "文件",
    #             help="已上传的文件名称",
    #         ),
    #         "file_selected": st.column_config.CheckboxColumn(
    #             "选择",
    #             help="选择需要解读的文件",
    #             default=False,
    #         )
    #     },
    #     disabled=["file_name"],
    #     hide_index=True,
    # )

    # dred(f'file_column_return_data: \n')
    # file_column_dict = file_column_return_data.to_dict()
    # file_column_return_data转换为dict后的格式
    # {
    #   'file_name': {
    #       0: '导游-欧洲行注意事项.txt',
    #       1: '4.29 荷法瑞意+新天鹅堡+花季赏花9晚11日（法签）(1).md'
    #   },
    #   'file_selected': {
    #       0: True,
    #       1: True
    #   }
    # }
    # dred(file_column_dict)

def on_clear_files():
    dred('files cleared.')
    st.session_state.session_data['paras']['files'] = []
    st.session_state.session_data['paras']['file_column_raw_data'] = {}

def on_connecting_internet_change():
    s_paras = st.session_state.session_data['paras']
    s_paras['connecting_internet'] = not s_paras['connecting_internet']

def on_use_think_model_change():
    s_paras = st.session_state.session_data['paras']
    s_paras['use_think_model'] = not s_paras['use_think_model']

def on_draw_change():
    s_paras = st.session_state.session_data['paras']
    s_paras['draw'] = not s_paras['draw']

def on_is_agent_change():
    s_paras = st.session_state.session_data['paras']
    s_paras['is_agent'] = not s_paras['is_agent']

def on_latex_change():
    s_paras = st.session_state.session_data['paras']
    s_paras['latex'] = not s_paras['latex']

# def on_input_translate_change():
#     s_paras = st.session_state.session_data['paras']
#     s_paras['input_translate'] = not s_paras['input_translate']

def on_main_llm_change():
    s_paras = st.session_state.session_data['paras']
    # s_paras['main_llm_url'] = value

    refreshed = mem_llm.refresh_endpoint(
        s_paras['main_llm_url'],
        s_paras['main_llm_key'],
        s_paras['main_llm_model_id'],
    )
    # if refreshed:
    #     # 更换llm成功时，清空屏幕内容和llm记忆
    #     on_clear_history()
    #     dred('on_clear_history() by on_main_llm_url_change()')

# def on_english_llm_change():
#     s_paras = st.session_state.session_data['paras']
#     # s_paras['english_llm_url'] = value
#
#     if s_paras['input_translate']:
#         refreshed = mem_llm.refresh_endpoint(
#             st.session_state.session_data['paras']['english_llm_url'],
#             st.session_state.session_data['paras']['english_llm_key'],
#             st.session_state.session_data['paras']['english_llm_model_id'],
#         )


def on_temperature_change():
    s_paras = st.session_state.session_data['paras']
    s_paras['local_llm_temperature'] = st.session_state.local_llm_temperature


def on_max_new_token_change():
    s_paras = st.session_state.session_data['paras']
    s_paras['local_llm_max_new_token'] = st.session_state.local_llm_max_new_token

def on_concurrent_num_change():
    s_paras = st.session_state.session_data['paras']
    s_paras['concurrent_num'] = st.session_state.concurrent_num

def streamlit_refresh_loop():
    # dred('----------------111---------------')
    session_state_init()

    first_page_on_load = st.session_state['first_page_on_load']
    if first_page_on_load == True :
        dgreen(f'first_page_on_load = {first_page_on_load}')
        load_pickle_on_refresh()

    # st.header('Default Options')
    # event = st_file_browser(
    #     path='/home/tutu/file_server',
    #     key='A',
    #     # show_preview_top=True,
    #     # show_choose_file=True,
    #     # show_download_file=True,
    #     # show_new_folder=True,
    #     show_upload_file=True,
    #     use_static_file_server=True,
    # )
    # st.write(event)

    s_paras = st.session_state.session_data['paras']
    # =============================侧栏==============================
    sidebar = st.sidebar
    # =============================expander：对话参数==============================
    exp1 =  sidebar.expander("对话参数", expanded=True)
    s_paras['url_prompt'] = exp1.text_input(label="URL:", label_visibility='collapsed', placeholder="请在这里输入您需要LLM解读的URL", value=s_paras['url_prompt'])
    s_paras['multi_line_prompt'] = exp1.text_area(label="多行指令:", label_visibility='collapsed', placeholder="请在这里输入您的多行指令", value=s_paras['multi_line_prompt'], disabled=st.session_state.processing)

    dred('---------refresh时的paras----------')
    pprint.pprint(s_paras)
    dred('----------------------------------')

    col0, col1, col11, col2, col3, col4, col5 = exp1.columns([1, 1, 1, 1, 1, 1, 1])
    col0.checkbox('Agent', value=s_paras['is_agent'], disabled=st.session_state.processing, on_change=on_is_agent_change)
    col1.checkbox('联网', value=s_paras['connecting_internet'], disabled=st.session_state.processing, on_change=on_connecting_internet_change)
    col11.checkbox('公式', value=s_paras['latex'], disabled=st.session_state.processing, on_change=on_latex_change)
    col2.checkbox('绘画', value=s_paras['draw'], disabled=st.session_state.processing, on_change=on_draw_change)
    # connecting_internet_detail = col2.checkbox('明细', value=False, disabled=st.session_state.processing)
    col3.button("清空", on_click=on_clear_history, disabled=st.session_state.processing, key='clear_button')
    col4.button("中止", on_click=on_cancel_response, disabled=not st.session_state.processing, key='cancel_button')
    col5.button("发送", on_click=on_chat_input_submit, args=(s_paras['multi_line_prompt'],), disabled=st.session_state.processing, key='confirm_button')
    exp1.slider('temperature:', 0.0, 1.0, s_paras['local_llm_temperature'], step=0.1, format='%.1f', disabled=st.session_state.processing, on_change=on_temperature_change, key='local_llm_temperature')
    exp1.slider('max_new_tokens:', 256, 32768, s_paras['local_llm_max_new_token'], step=4096, disabled=st.session_state.processing, on_change=on_max_new_token_change, key='local_llm_max_new_token')
    exp1.slider('联网并发数量:', 2, 10, s_paras['concurrent_num'], disabled=st.session_state.processing, on_change=on_concurrent_num_change, key='concurrent_num')

    c10, c11, c12, c13, c14, c15, c16 = exp1.columns([1, 1, 1, 1, 1, 1, 1])
    c10.checkbox('深度', value=s_paras['use_think_model'], disabled=st.session_state.processing, on_change=on_use_think_model_change)

    # =============================expander：文档管理==============================
    exp2 =  sidebar.expander("文档管理", expanded=True)
    # st_display_pdf("/home/tutu/3.pdf")
    s_paras['files'] = exp2.file_uploader(
        "选择待上传的文件",
        accept_multiple_files=True,
        type=['sh', 'md', 'txt', 'jpg', 'jpeg', 'png', 'bmp'],
        # on_change=refresh_file_column,
        # kwargs={
        #     'in_widget':exp2,
        #     'in_files':s_paras['files'],
        #     'file_uploader_changed':True,
        # },
    )
    refresh_file_column(in_widget=exp2, in_files=s_paras['files'])
    if st.session_state.session_data['paras']['file_column_raw_data']:
        exp2.data_editor(
            pd.DataFrame(st.session_state.session_data['paras']['file_column_raw_data']),
            column_config={
                "file_name": st.column_config.TextColumn(
                    "文件",
                    help="已上传的文件名称",
                ),
                "file_selected": st.column_config.CheckboxColumn(
                    "选择",
                    help="选择需要解读的文件",
                    default=False,
                )
            },
            disabled=["file_name"],
            hide_index=True,
        )
    exp2.button("清空文件", on_click=on_clear_files, disabled=st.session_state.processing, key='clear_files_button')

    # if s_paras['files'] is not None:

        # =======由于file_uploader无法在页面启动时设置默认文件列表，因此这里添加额外的文件列表显示=======
        # if len(s_paras['files']) > 0:
        #     df_file_list = pd.DataFrame(
        #         {
        #             # "file_name": ['1','2','3'],   # string
        #             # "file_selected": [True,True,True],   # bool
        #             "file_name": [f.name for f in s_paras['files']],   # string
        #             "file_selected": [True for f in s_paras['files']],   # bool
        #         }
        #     )
        #     dred(df_file_list)
        #     exp2.data_editor(
        #         df_file_list,
        #         column_config={
        #             "file_name": st.column_config.TextColumn(
        #                 "文件",
        #                 help="已上传的文件名称",
        #             ),
        #             "file_selected": st.column_config.CheckboxColumn(
        #                 "选择",
        #                 help="选择需要解读的文件",
        #                 default=False,
        #             )
        #         },
        #         disabled=["file_name"],
        #         hide_index=True,
        #     )

        # for f in s_paras['files']:
        #     dgreen(f'读取"{f.name}"成功.')
        #     print(f)
            # content = StringIO(f.getvalue().decode("utf-8")).read()

            # 显示文件内容
            # dred(content)
            # st.markdown(content)

            # with f.NamedTemporaryFile(delete=False) as tmp_file:
            #     dgreen(tmp_file.name)
            # st_display_pdf(f)

        # ==============================================================================


    # =============================expander：角色参数==============================
    exp3 =  sidebar.expander("Prompt 参数", expanded=True)
    s_paras['system_prompt'] = exp3.text_input(label="设置系统提示:", label_visibility='collapsed', placeholder="请在这里输入您的系统提示", value=s_paras['system_prompt'])
    s_paras['role_prompt'] = exp3.text_area(label="设置角色提示:", label_visibility='collapsed', placeholder="请在这里输入您的角色提示", value=s_paras['role_prompt'], disabled=st.session_state.processing)

    # =============================主模型、辅模型(用于翻译input)==============================
    exp4 =  sidebar.expander("模型API 参数", expanded=True)
    # 注意：用on_change回调的话，回调的瞬间，s_paras['main_llm_url']中的值是change之前的
    s_paras['main_llm_url'] = exp4.text_input(label="URL:", placeholder="http(s)://ip:port/v1/", value=s_paras['main_llm_url'])
    s_paras['main_llm_key'] = exp4.text_input(label="API-key:", placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", value=s_paras['main_llm_key'])
    s_paras['main_llm_model_id'] = exp4.text_input(label="id:", placeholder="model_id", value=s_paras['main_llm_model_id'])
    if s_paras['main_llm_url'] or s_paras['main_llm_key'] or s_paras['main_llm_model_id']:
        on_main_llm_change()
    # if not 'input_translate' in s_paras or not s_paras['input_translate']:
    #     # 当调用英语模型时，由于mem_llm的url经过refresh变成了英语模型，因此这里如果refresh为主模型会发现不一致从而清除历史
    #     refreshed = mem_llm.refresh_endpoint(
    #         s_paras['main_llm_url'],
    #         s_paras['main_llm_key'],
    #         s_paras['main_llm_model_id'],
    #     )
    #     if refreshed:
    #         # 更换llm成功时，清空屏幕内容和llm记忆
    #         on_clear_history()
    #         dred('on_clear_history() by input_translate')
    #         dred(f'input_translate in s_paras: {"input_translate" in s_paras}')
    #         dred(f's_paras["input_translate"]: {s_paras["input_translate"]}')

    # exp4.checkbox('调用擅长英语的模型', value=s_paras['input_translate'], on_change=on_input_translate_change)
    # s_paras['english_llm_url'] = exp4.text_input(label="英语模型:", placeholder="http(s)://ip:port/v1/", value=s_paras['english_llm_url'], disabled=not s_paras['input_translate'])
    # s_paras['english_llm_key'] = exp4.text_input(label="英语模型key:", placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", value=s_paras['english_llm_key'], disabled=not s_paras['input_translate'])
    # s_paras['english_llm_model_id'] = exp4.text_input(label="英语模型model_id:", placeholder="model_id", value=s_paras['english_llm_model_id'], disabled=not s_paras['input_translate'])
    # if s_paras['english_llm_url'] or s_paras['english_llm_key'] or s_paras['english_llm_model_id']:
    #     on_english_llm_change()

    # =======================所有chat历史的显示========================
    # 这一行必须要运行，不能加前置判断，否则chat_input没有显示
    chat_input_prompt = st.chat_input("请在这里输入您的指令", on_submit=on_chat_input_submit)
    if st.session_state.prompt:
        # 侧栏有输入时，以侧栏prompt为准（注意：侧栏完成输出后，st.session_state.prompt必须清空）
        pass
    else:
        # 侧栏没有输入时，以chat_input prompt为准
        st.session_state.prompt = chat_input_prompt

    for message in st.session_state.session_data['msgs']:
        if type(message)==dict:
            # print(f'dict message: {message}')
            print(f'--------------{message}-----------------')
            if message.get('type') and message['type'] == 'image':
                st.image(message['content'])
            if message.get('type') and message['type'] == 'video':
                st.image(message['content'])
            if message.get('type') and message['type']=='status':
                # 添加已完成的status
                status_title = message['title']
                status_list = message['status_list']
                status = st.status(label=status_title, state='complete', expanded=False)
                for s in status_list:
                    status.markdown(s)
            elif message.get('type') and message['type']=='pics':
                # 添加图片list
                for img in message['data']:
                    st.image(img['data'], caption=img['caption'], use_column_width=True)
            elif message.get('type') and message['type'] == 'latex':
                with st.chat_message(message['role']):
                    st.latex(message['content'])
                    # show_string_container_latex(st, message['content'])

            elif message.get('type') and message['type'] == 'text':
                with st.chat_message(message['role']):
                    st.markdown(message['content'])
            else:
                with st.chat_message(message['role']):
                    st.markdown(message['content'])

        elif type(message)==list:
            print(f'message: {message}')
            for item in message:
                if item['type']=='image':
                    st.image(item['url'])
                if item['type']=='video':
                    st.markdown(item['url'])
            # with st.chat_message('assistant'):
            #     num = len(message)
            #     cols = st.columns([1]*num)
            #     i=0
            #     for col in cols:
            #         col.markdown(message[i])
            #         # col.container(border=True).markdown(message[i])
            #         i += 1

        # st.status('测试下status')

    if st.session_state.prompt and st.session_state.processing:

        # =======================user输入的显示=======================
        with st.chat_message('user'):
            st.markdown(st.session_state.prompt)
        # =====================user输入的状态存储======================
        st.session_state.session_data['msgs'].append({
            'role': 'user',
            'content': st.session_state.prompt
        })

        # with st.chat_message('assistant'):
        # status_data, async_llms, completed_answer = ask_llm(
        #     st.session_state.prompt,
        #     role_prompt,
        #     st.session_state.url_prompt,
        #     connecting_internet,
        #     is_agent,
        #     system_prompt,
        #     files
        # )
        status_data, async_llms, completed_answer, images_data = ask_llm(st.session_state.prompt, st.session_state.session_data['paras'])
        # status_data, async_llms, completed_answer = llm_response_concurrently(st.session_state.prompt, role_prompt, connecting_internet, connecting_internet_detail, is_agent)

        dgreen(f'completed_answer: {completed_answer}')
        # ==================assistant输出的状态存储====================
        if status_data:
            st.session_state.session_data['msgs'].append(status_data)
        if async_llms:
            num = len(async_llms)
            st.session_state.session_data['msgs'].append([async_llms[i].get_final_response() for i in range(num)])
        if completed_answer:
            if type(completed_answer) == dict:
                print(f'----------completed_answer1---------\n{completed_answer["content"]}')
                my_str = completed_answer['content'].replace(r"\(", '').replace(r"\)", '').replace(r"\[", '').replace(r"\]", '')
                print(f'----------completed_answer11---------\n{my_str}')
                st.session_state.session_data['msgs'].append({
                    'role': 'assistant',
                    'content': completed_answer['content'] ,
                    'type': completed_answer['type']
                })
            elif type(completed_answer) is str:
                print(f'----------completed_answer12---------\n{completed_answer}')
                st.session_state.session_data['msgs'].append({
                    'role': 'assistant',
                    'content': completed_answer,
                    'type': 'text'
                })
        if images_data:
            st.session_state.session_data['msgs'].append(images_data)

        # 存储会话文件
        # get_session_id()
        # st.session_state.session_data = {
        #     'session_id': st.session_state.sid,
        #     'msgs': st.session_state.session_data['msgs'],
        #     'paras': st.session_state.paras,
        # }
        save_pickle()


        # ===================完成输出任务后，通过rerun来刷新一些按钮的状态========================
        # print('=======================任务完成后的刷新( st.rerun() )==============================')
        st.session_state.processing = False
        st.session_state.prompt = ''
        st.rerun()

    st.session_state['first_page_on_load'] = False

if __name__ == "__main__" :
    streamlit_refresh_loop()