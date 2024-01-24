import streamlit as st
from tools.llm.api_client import LLM_Client, Concurrent_LLMs, Async_LLM

import time
import asyncio

import base64
from pathlib import Path
import tempfile

from tools.retriever.search import Bing_Searcher
from utils.long_content_summary import long_content_qa

# 包方式运行：python -m streamlit run gpu_server/llm_webui_streamlit_server.py --server.port 7860

# 配置(必须第一个调用)
st.set_page_config(
    initial_sidebar_state="collapsed",
    page_title="Phind-34B-V2",
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
def streamlit_init():
    LLM_Client.Set_All_LLM_Server('http://127.0.0.1:8002/v1')
    print(f'llm_webui_streamlit_server_phind:streamlit_init:Get_All_LLM_Server() = "{LLM_Client.Get_All_LLM_Server()}"')
    mem_llm = LLM_Client(
        history=True,  # 这里要关掉server侧llm的history，对话历史由用户session控制
        print_input=False,
        temperature=0,
    )
    return mem_llm

def session_state_init():
    # 状态的初始化

    if 'processing' not in st.session_state:
        print('=================================状态初始化==================================')
        st.session_state['processing'] = False
        print(f'st.session_state.processing = {st.session_state.processing}')
        
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []
        print(f'st.session_state.messages = {st.session_state.messages}')

    if 'prompt' not in st.session_state:
        st.session_state['prompt'] = ''
        print(f'st.session_state.prompt = "{st.session_state.prompt}"')
        # print('=============================================================================')
    
# 返回searcher及其loop
# 这里不能用@st.cache_resource，否则每次搜索结果都不变
# @st.cache_resource
def search_init(concurrent_num=3):
    import sys, platform
    fix_streamlit_in_win = True if sys.platform.startswith('win') else False
    return Bing_Searcher.create_searcher_and_loop(fix_streamlit_in_win, in_search_num=concurrent_num)   # 返回loop，主要是为了在searcher完成start后，在同一个loop中执行query_bing_and_get_results()

# asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
mem_llm = streamlit_init()

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
            in_temperature= st.session_state.local_llm_temperature,
        )
        async_llm.start()
    return async_llms

def llm_response_concurrently(prompt, role_prompt, connecting_internet):
    # =================================搜索并llm=================================
    if connecting_internet:
        # =================================搜索=================================
        status = st.status(label=":green[启动联网解读任务...]", expanded=False)

        assistant = st.chat_message('assistant')
        if not st.session_state.get('local_llm_concurrent_num'):
            st.session_state.local_llm_concurrent_num = 3
        async_llms = async_llm_local_response_concurrently(
            in_st=assistant,
            in_prompt=prompt,
            in_role_prompt=role_prompt,
            in_concurrent_num=st.session_state.local_llm_concurrent_num,
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
        
        status.markdown("搜索引擎bing.com调用中...")

        searcher = search_init(st.session_state.concurrent_num)
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
        return async_llms, final_answer
    else:
        # =================================local llm=================================
        place_holder = st.chat_message('assistant').empty()
        mem_llm.set_role_prompt(role_prompt)
        full_res = ''
        for res in mem_llm.ask_prepare(
            in_question=prompt, 
            in_temperature=st.session_state.local_llm_temperature,
            in_max_new_tokens=st.session_state.local_llm_max_new_token,
        ).get_answer_generator():
            full_res += res
            place_holder.markdown(full_res)
        return None, full_res

def on_clear_history():
    st.session_state.messages = []
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
    print('=================================状态刷新==================================')
    print(f'st.session_state.processing = {st.session_state.processing}')
    # print('============================================================================')

def st_display_pdf(pdf_file):
    with open(pdf_file, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="800" height="1000" type="application/pdf">'
    st.markdown(pdf_display, unsafe_allow_html=True)
    
def streamlit_refresh_loop():
    session_state_init()
    on_refresh()
    # =============================侧栏==============================
    sidebar = st.sidebar
    # =============================expander：对话参数==============================
    exp1 =  sidebar.expander("对话参数", expanded=True)
    multi_line_prompt = exp1.text_area(label="多行指令:", label_visibility='collapsed', placeholder="请在这里输入您的多行指令", value="", disabled=st.session_state.processing)
    
    col0, col1, col2, col3 = exp1.columns([2, 1, 1, 1])
    connecting_internet = col0.checkbox('联网', value=True, disabled=st.session_state.processing)
    col1.button("清空", on_click=on_clear_history, disabled=st.session_state.processing, key='clear_button')
    col2.button("中止", on_click=on_cancel_response, disabled=not st.session_state.processing, key='cancel_button')
    col3.button("发送", on_click=on_chat_input_submit, args=(multi_line_prompt,), disabled=st.session_state.processing, key='confirm_button')
    st.session_state.local_llm_temperature = exp1.slider('temperature:', 0.0, 1.0, 0.7, step=0.1, format='%.1f', disabled=st.session_state.processing)
    st.session_state.local_llm_max_new_token = exp1.slider('max_new_tokens:', 256, 2048, 512, step=256, disabled=st.session_state.processing)
    st.session_state.concurrent_num = exp1.slider('联网并发数量:', 2, 10, 3, disabled=st.session_state.processing)

    # =============================expander：文档管理==============================
    exp2 =  sidebar.expander("文档管理", expanded=True)
    # st_display_pdf("/home/tutu/3.pdf")
    file = exp2.file_uploader("选择待上传的PDF文件", type=['pdf'])
    if file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            st_display_pdf(tmp_file.name)
                

    # =============================expander：角色参数==============================
    exp3 =  sidebar.expander("角色参数", expanded=True)
    role_prompt = exp3.text_area(label="设置角色提示:", label_visibility='collapsed', placeholder="请在这里输入您的角色提示", value="", disabled=st.session_state.processing)
    
    # =======================所有chat历史的显示========================
    # 这一行必须要运行，不能加前置判断，否则chat_input没有显示
    chat_input_prompt = st.chat_input("请在这里输入您的指令", on_submit=on_chat_input_submit)
    if st.session_state.prompt:
        # 侧栏有输入时，以侧栏prompt为准（注意：侧栏完成输出后，st.session_state.prompt必须清空）
        pass
    else:
        # 侧栏没有输入时，以chat_input prompt为准
        st.session_state.prompt = chat_input_prompt

    for message in st.session_state.messages:
        if type(message)==dict:
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

    if st.session_state.prompt and st.session_state.processing:
        # =======================user输入的显示=======================
        with st.chat_message('user'):
            st.markdown(st.session_state.prompt)
        # =====================user输入的状态存储======================
        st.session_state.messages.append({
            'role': 'user',
            'content': st.session_state.prompt
        })

        # with st.chat_message('assistant'):
        async_llms, completed_answer = llm_response_concurrently(st.session_state.prompt, role_prompt, connecting_internet)

        # ==================assistant输出的状态存储====================
        if async_llms:
            num = len(async_llms)
            st.session_state.messages.append([async_llms[i].get_final_response() for i in range(num)])
        if completed_answer:
            st.session_state.messages.append({
                'role': 'assistant',
            'content': completed_answer
            })

        # ===================完成输出任务后，通过rerun来刷新一些按钮的状态========================
        print('=======================任务完成后的刷新( st.rerun() )==============================')
        st.session_state.processing = False
        st.session_state.prompt = ''
        st.rerun()

if __name__ == "__main__" :
    streamlit_refresh_loop()