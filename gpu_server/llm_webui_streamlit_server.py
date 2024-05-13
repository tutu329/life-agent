import streamlit as st
import pandas as pd
# from streamlit_file_browser import st_file_browser

import config
from config import dred, dgreen, dblue, dcyan
from tools.llm.api_client import LLM_Client, Concurrent_LLMs, Async_LLM

from agent.tool_agent_prompts import Search_Tool, Code_Tool, Energy_Investment_Plan_Tool, QA_Url_Content_Tool
from agent.tool_agent import Tool_Agent

import time

import base64
from io import StringIO

from tools.qa.file_qa import files_qa

from tools.retriever.search import Bing_Searcher
from utils.decorator import timer

from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
from streamlit import runtime
from streamlit.web.server.websocket_headers import _get_websocket_headers
from utils.extract import get_ajs_anonymous_id_from_cookie
import pickle

# 包方式运行：python -m streamlit run gpu_server/llm_webui_streamlit_server.py --server.port 7860

# 配置(必须第一个调用)
st.set_page_config(
    initial_sidebar_state="collapsed",
    page_title="Life-Agent",
    layout="wide",
)
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
    # LLM_Client.Set_All_LLM_Server('http://127.0.0.1:8001/v1')
    # dgreen(f'初始化所有LLM的url_endpoint: ', end='', flush=True)
    # dblue(f'"{LLM_Client.Get_All_LLM_Server()}"')

    # 初始化 mem_llm
    history = True
    mem_llm = LLM_Client(
        url=config.Global.llm_url,
        api_key=config.Global.llm_key,
        model_id=config.Global.llm_model,
        history=history,  # 这里打开llm的history，对话历史与streamlit显示的内容区分开
        print_input=False,
    )
    mem_llm = LLM_Client(
        history=history,  # 这里打开llm的history，对话历史与streamlit显示的内容区分开
        print_input=False,
    )
    dgreen('初始化mem_llm完毕: ', end='', flush=True)
    # dblue(f'"history={history}, temperature(初始)={temperature}"')
    return mem_llm

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
        # dred(f'文件读取会话文件出错: "{e}"')
        st.session_state.session_data = default_session_data
        st.session_state.session_data['sid'] = sid

def save_pickle():
    # get_session_id()
    # dgreen(f'sd: \n{st.session_state}')
    sid = st.session_state.session_data['sid']

    work_dir = config.Global.get_work_dir() # "/home/tutu/server/life-agent"
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
        'connecting_internet': False,

        'local_llm_temperature': 0.7,
        'local_llm_max_new_token': 4096,
        'concurrent_num': 3,

        'files': [],                            # file_uploader返回的UploadedFile列表
        'last_files_num_of_file_uploader':0,    # 用于判断是否是file_uploader将files删光，用于和files没有而会话历史有文件数据的情况
        'file_column_raw_data': {},             # 用于管理和显示会话内UploadedFile数据
        'system_prompt': config.Global.llm_system,
        'role_prompt': '',
        'main_llm_url': config.Global.llm_url,
        'input_translate': False,
        'english_llm_url': config.Global.llm_url2,
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
mem_llm = llm_init()

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

@timer
def ask_llm(prompt, paras):
    role_prompt = paras['role_prompt']
    url_prompt = paras['url_prompt']
    connecting_internet = paras['connecting_internet']
    is_agent = paras['is_agent']
    system_prompt = paras['system_prompt']
    files = paras['files']
# def llm_response_concurrently(prompt, role_prompt, connecting_internet, connecting_internet_detail, is_agent):
    # =================================agent功能=================================
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

        # LLM_Client.Set_All_LLM_Server('http://116.62.63.204:8001/v1')
        tools = [Search_Tool, Code_Tool, Energy_Investment_Plan_Tool, QA_Url_Content_Tool]
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
            in_output_stream_buf=placeholder1.markdown,
        )
        agent.init()
        success = agent.run()
        print(f'final_answer_list: {final_answer_list}')
        status_list = status_data["status_list"]
        print(f'status_list: {status_list}')

        status.update(label=f":green[Agent已完成任务]", state='complete', expanded=True)
        return status_data, None, '\n'.join(final_answer_list)
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
    #     return status_data, None, final_answer
    # =================================搜索并llm=================================
    if connecting_internet:
        # =================================搜索=================================
        status = st.status(label=":green[启动联网解读任务...]", expanded=False)
        status.markdown("搜索引擎bing.com调用中...")
        assistant = st.chat_message('assistant')

        # if not connecting_internet_detail:
        #     # 不包含明细的联网搜索和解读
        #     placeholder1 = assistant.empty()
        #     # searcher = search_init(concurrent_num=st.session_state.concurrent_num)
        #     # print(f'********1 placeholder.markdown: {placeholder.markdown}')
        #     searcher = search_init(concurrent_num=st.session_state.concurrent_num, in_stream_buf_callback=assistant.empty().markdown)
        #     rtn, search_urls = searcher.legacy_search_and_ask(prompt)
        #
        #     final_answer = ''
        #     placeholder2 = assistant.empty()
        #     # print(f'********2 placeholder.markdown: {placeholder.markdown}')
        #     for chunk in rtn.get_answer_generator():
        #         final_answer += chunk
        #         placeholder2.markdown(final_answer + searcher.flicker.get_flicker())
        #     placeholder2.markdown('\n\n')
        #     final_answer += '\n\n'
        #     i = 0
        #     print(f'-------------------------------{search_urls}+++++++++++++')
        #     for search_url in search_urls:
        #         i += 1
        #         url_md = f'[{search_url[:30]}...]({search_url} "{search_url}")'
        #         url_string = f'【{i}】{url_md} \n\n'
        #         final_answer += url_string
        #         placeholder2.markdown(url_string)
        #
        #     return None, None, final_answer

        searcher = search_init(concurrent_num=st.session_state.session_data['paras']['concurrent_num'])

        async_llms = async_llm_local_response_concurrently(
            in_st=assistant,
            in_prompt=prompt,
            in_role_prompt=role_prompt,
            in_concurrent_num=st.session_state.session_data['paras']['concurrent_num'],
        )
        # 非联网llm调用，用于和联网llm解读结果对比
        #async_llm = Async_LLM()
        #async_llm.init(
        #    assistant.empty().markdown, 
        #    prompt, 
        #    in_role_prompt=role_prompt,
        #    in_extra_suffix=' ${}^{【local】}$ \n\n',
        #    in_streamlit=True
        #)
        #async_llm.start()
        
        internet_search_result = searcher.search(prompt)
        # print(f'internet_search_result: {internet_search_result}')
        status.markdown("搜索引擎bing.com调用完毕.")

        # 为调用Concurrent_LLMs准备输入参数
        num = len(internet_search_result)
        prompts = [prompt]*(num)    # 所有的question
        suffixes = []
        contents = []
        callbacks = []

        # 显示非联网的解读结果stream[0]作为参考、以及所有联网解读结果stream[k]
        # assistant = st.chat_message('assistant')
        first_placeholder = None
        for i in range(num):
            # 所有需要理解的文本（需要嵌入question）
            content = '\n'.join(internet_search_result[i][1])
            contents.append(content)
            # 所有llm的stream输出用的bufs，注意这里需要在st.chat_message('assistant')下生成stream
            placeholder = assistant.empty()
            if i==0:
                first_placeholder = placeholder
            callbacks.append(placeholder.markdown)

            url = internet_search_result[i][0]
            url_md = f'[{url[:30]}...]({url} "{url}") \n\n'
            index = f'【{i+1}】'
            suffix = '\n\n${}^{' + index + '}$' + url_md + '\n\n'    # 用markdown格式显示[1]为上标
            suffixes.append(suffix)
        # 用于显示临时信息，vllm全速输出时，会覆盖这个临时信息
        # first_placeholder.markdown('解读结果即将返回...')

        # 初始化Concurrent_LLMs并运行输出status
        llms = Concurrent_LLMs()
        llms.init(prompts, contents, callbacks, in_extra_suffixes=suffixes)
        for task_status in llms.start_and_get_status():
            status.update(label=f":green[{task_status['describe']}]", state=task_status['type'], expanded=False)
            status.markdown(task_status['detail'])


        for llm in async_llms:
            llm.wait()

        # 将完整的输出结果，返回
        final_answer = ''
        # final_answer += async_llm.final_response
        for answer in task_status['llms_full_responses']:
            # 这里task_status是llms.start_and_get_status()结束后的最终状态
            final_answer += answer
        return None, async_llms, final_answer
    else:
        # =================================local llm=================================
        all_prompt = role_prompt
        mem_llm.set_role_prompt(all_prompt)

        if url_prompt:
            # 如果填了url
            searcher = Bing_Searcher.create_searcher_and_loop()
            result = searcher.loop.run_until_complete(searcher.get_url_content(in_url=url_prompt))
            all_prompt = f'请严格根据URL(网页链接)返回的内容回答问题, URL(网页链接)返回的具体内容为: \n#############################################\n"{result}"\n#############################################\n'
            mem_llm.set_role_prompt(all_prompt)

        files_info_dict = st.session_state.session_data['paras']['file_column_raw_data']
        if 'file_content' in files_info_dict:
            # result = StringIO(f.getvalue().decode("utf-8")).read()
            result = files_info_dict['file_content'][0]
            dred(f'===========file_content===========\n"{result}"')
            fname = files_info_dict['file_name'][0]
            all_prompt = f'请严格根据文件({fname})返回的内容回答问题, 文件返回的具体内容为: "{result}"'
            mem_llm.set_role_prompt(all_prompt)

            # ans = mem_llm.ask_prepare(
            #     in_question='文件目录返回给我',
            #     in_temperature=st.session_state.local_llm_temperature,
            #     in_max_new_tokens=st.session_state.local_llm_max_new_token,
            #     in_system_prompt=system_prompt,
            # ).get_answer_and_sync_print()
            # st.markdown(ans)

        place_holder = st.chat_message('assistant').empty()
        full_res = ''

        # 如果需要将query翻译为英文，并调用擅长英语的模型
        if st.session_state.session_data['paras']['input_translate']:
            translate_llm = LLM_Client(
                history=False,
                url=st.session_state.session_data['paras']['main_llm_url'],
                print_input=False,
            )

            dblue(f'需翻译的输入: "{prompt}"')
            # translate_llm.set_role_prompt('不管输入是什么，你都不会对输入的内容进行解读，都直接将输入翻译为英文，且绝对不增加额外的引号')
            translated_input = translate_llm.ask_prepare(
                in_question=f'将"{prompt}"翻译为英文，不要增加额外的引号',
                in_temperature = st.session_state.session_data['paras']['local_llm_temperature'],
                in_max_new_tokens=st.session_state.session_data['paras']['local_llm_max_new_token'],
                in_system_prompt = '你擅长将中文翻译为英语'
            ).get_answer_and_sync_print()
            dblue(f'翻译后的输入: "{translated_input}"')

            prompt = translated_input

            mem_llm.refresh_url(st.session_state.session_data['paras']['english_llm_url'])


        # llm输出、统计输出时间
        start_time1 = time.time()

        gen = mem_llm.ask_prepare(
            in_question=prompt, 
            in_temperature=st.session_state.session_data['paras']['local_llm_temperature'],
            in_max_new_tokens=st.session_state.session_data['paras']['local_llm_max_new_token'],
            in_system_prompt=system_prompt,
        ).get_answer_generator()


        wait_first_token = True
        for res in gen:
            if res and wait_first_token:
                start_time2 = time.time()
                wait_first_token = False

            full_res += res
            place_holder.markdown(full_res)

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
            full_res += f'\n\n:green[{all_tokens} ( {p_tokens} + {c_tokens} ) tokens in {all_time_str} ( {input_time_str} + {output_time_str} ) secs, {input_ts_str} t/s, {output_ts_str} t/s ]'
            # full_res += f'\n\n:green[( {p_tokens}输入 + {c_tokens}输出 = {p_tokens+c_tokens} tokens )]'
        except Exception as e:
            dred(f'统计时间为0.')


        place_holder.markdown(full_res)
        return None, None, full_res

def on_clear_history():
    # st.session_state.messages = []
    st.session_state.session_data['msgs'] = []
    save_pickle()
    mem_llm.clear_history()

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
            file_column_raw_data = {
                "file_name": [f.name for f in in_files],                                            # string
                "file_selected": [True for f in in_files],                                          # bool
                "file_content":[StringIO(f.getvalue().decode("utf-8")).read() for f in in_files],   # string of file content
            }
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

def on_is_agent_change():
    s_paras = st.session_state.session_data['paras']
    s_paras['is_agent'] = not s_paras['is_agent']

def on_input_translate_change():
    s_paras = st.session_state.session_data['paras']
    s_paras['input_translate'] = not s_paras['input_translate']


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

    col0, col1, col2, col3, col4, col5 = exp1.columns([1, 1, 1, 1, 1, 1])
    col0.checkbox('Agent', value=s_paras['is_agent'], disabled=st.session_state.processing, on_change=on_is_agent_change)
    col1.checkbox('联网', value=s_paras['connecting_internet'], disabled=st.session_state.processing, on_change=on_connecting_internet_change)
    # connecting_internet_detail = col2.checkbox('明细', value=False, disabled=st.session_state.processing)
    col3.button("清空", on_click=on_clear_history, disabled=st.session_state.processing, key='clear_button')
    col4.button("中止", on_click=on_cancel_response, disabled=not st.session_state.processing, key='cancel_button')
    col5.button("发送", on_click=on_chat_input_submit, args=(s_paras['multi_line_prompt'],), disabled=st.session_state.processing, key='confirm_button')
    exp1.slider('temperature:', 0.0, 1.0, s_paras['local_llm_temperature'], step=0.1, format='%.1f', disabled=st.session_state.processing, on_change=on_temperature_change, key='local_llm_temperature')
    exp1.slider('max_new_tokens:', 256, 4096, s_paras['local_llm_max_new_token'], step=256, disabled=st.session_state.processing, on_change=on_max_new_token_change, key='local_llm_max_new_token')
    exp1.slider('联网并发数量:', 2, 10, s_paras['concurrent_num'], disabled=st.session_state.processing, on_change=on_concurrent_num_change, key='concurrent_num')

    # =============================expander：文档管理==============================
    exp2 =  sidebar.expander("文档管理", expanded=True)
    # st_display_pdf("/home/tutu/3.pdf")
    s_paras['files'] = exp2.file_uploader(
        "选择待上传的文件",
        accept_multiple_files=True,
        type=['sh', 'md', 'txt'],
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
    s_paras['main_llm_url'] = exp4.text_input(label="主模型:", placeholder="http(s)://ip:port/v1", value=s_paras['main_llm_url'])
    if not 'input_translate' in s_paras or not s_paras['input_translate']:
        # 当调用英语模型时，由于mem_llm的url经过refresh变成了英语模型，因此这里如果refresh为主模型会发现不一致从而清除历史
        refreshed = mem_llm.refresh_url(s_paras['main_llm_url'])
        if refreshed:
            # 更换llm成功时，清空屏幕内容和llm记忆
            on_clear_history()

    exp4.checkbox('调用擅长英语的模型', value=s_paras['input_translate'], on_change=on_input_translate_change)
    s_paras['english_llm_url'] = exp4.text_input(label="英语模型:", placeholder="http(s)://ip:port/v1", value=s_paras['english_llm_url'], disabled=not s_paras['input_translate'])

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
            if message.get('type') and message['type']=='status':
                # 添加已完成的status
                status_title = message['title']
                status_list = message['status_list']
                status = st.status(label=status_title, state='complete', expanded=False)
                for s in status_list:
                    status.markdown(s)
            else:
                with st.chat_message(message['role']):
                    st.markdown(message['content'])
        elif type(message)==list:
            with st.chat_message('assistant'):
                num = len(message)
                cols = st.columns([1]*num)
                i=0
                for col in cols:
                    col.markdown(message[i])
                    # col.container(border=True).markdown(message[i])
                    i += 1
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
        status_data, async_llms, completed_answer = ask_llm(st.session_state.prompt, st.session_state.session_data['paras'])
        # status_data, async_llms, completed_answer = llm_response_concurrently(st.session_state.prompt, role_prompt, connecting_internet, connecting_internet_detail, is_agent)

        # ==================assistant输出的状态存储====================
        if status_data:
            st.session_state.session_data['msgs'].append(status_data)
        if async_llms:
            num = len(async_llms)
            st.session_state.session_data['msgs'].append([async_llms[i].get_final_response() for i in range(num)])
        if completed_answer:
            st.session_state.session_data['msgs'].append({
                'role': 'assistant',
                'content': completed_answer
            })

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