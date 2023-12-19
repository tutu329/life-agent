import streamlit as st
from tools.llm.api_client import LLM_Client

import time
import asyncio
from tools.retriever.search import Bing_Searcher

from utils.long_content_summary import long_content_summary

# 包方式运行：python -m streamlit run gpu_server/llm_webui_streamlit_server.py --server.port 7860

# 配置(必须第一个调用)
st.set_page_config(
    # initial_sidebar_state="collapsed",
    page_title="Qwen-72B",
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
    return LLM_Client(
        history=True,  # 这里要关掉server侧llm的history，对话历史由用户session控制
        need_print=False,
        temperature=0,
    ), ''

# 返回searcher及其loop
# 这里不能用@st.cache_resource，否则每次搜索结果都不变
# @st.cache_resource
def search_init():
    import sys, platform
    fix_streamlit_in_win = True if sys.platform.startswith('win') else False
    return Bing_Searcher.create_searcher_and_loop(fix_streamlit_in_win)   # 返回loop，主要是为了在searcher完成start后，在同一个loop中执行query_bing_and_get_results()

# asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
llm, user_query = llm_init()

def llm_response(prompt, role_prompt, connecting_internet):
    llm.set_role_prompt(role_prompt)

    # =================================搜索并llm=================================
    if connecting_internet:
        # =================================搜索=================================
        with st.status(":green[启动联网解读任务...]", expanded=True) as status:
            st.markdown("{搜索引擎bing.com调用中...}")
            # st.write("<搜索引擎bing.com调用中...>")

            print(f'==================================================================1\prompt: {prompt}===================================================================')
            searcher = search_init()
            internet_search_result = searcher.search_long_time(prompt)
            print(f'internet_search_result: {internet_search_result}')
            print('======================3=======================')

        # =================================llm=================================
            st.markdown("{搜索引擎bing.com调用完毕.}")
            url_idx = 0
            found = False
            for url, content_para_list in internet_search_result:
                url_idx += 1
                st.markdown(f"<搜索结果[{url_idx}]解读中...>")
                found = True

                temp_llm = LLM_Client(history=False, need_print=False, temperature=0)
                content = " ".join(content_para_list)
                prompt = f'这是网络搜索结果: "{content}", 请根据该搜索结果用中文回答用户的提问: "{prompt}"，回复要简明扼要、层次清晰、采用markdown格式。'
                gen = long_content_summary(temp_llm, prompt)
                # gen = temp_llm.ask_prepare(prompt).get_answer_generator()
                st.markdown(f"<搜索结果[{url_idx}]解读完毕.>")
                for chunk in gen:
                    yield chunk
                yield f'\n\n出处[{url_idx}]: ' + url + '\n\n'
                # st.write(f'\n\n出处[{url_idx}]: ' + url + '\n\n')

            status.update(label="联网解读任务完成.", state="complete", expanded=False)
    else:
    # =================================仅llm=================================
        gen = llm.ask_prepare(prompt).get_answer_generator()
        for chunk in gen:
            yield chunk


def on_clear_history():
    st.session_state.messages = []
    llm.clear_history()

def on_cancel_response():
    llm.cancel_response()

# def on_confirm_response(user_query, role_prompt, connecting_internet):
#     if 'messages' not in st.session_state:
#         st.session_state.messages = []
#     for message in st.session_state.messages:
#         with st.chat_message(message['role']):
#             st.markdown(message['content'])
#
#     if user_query:
#         # =======================user输入的显示=======================
#         with st.chat_message('user'):
#             st.markdown(user_query)
#         # =====================user输入的状态存储======================
#         st.session_state.messages.append({
#             'role': 'user',
#             'content': user_query
#         })
#
#         # ====================assistant输出的显示=====================
#         with st.chat_message('assistant'):
#             message_placeholder = st.empty()
#             full_response = ''
#             for res in llm_response(user_query, role_prompt, connecting_internet):
#                 full_response += res
#                 message_placeholder.markdown(full_response + '█ ')
#             message_placeholder.markdown(full_response)
#         # ==================assistant输出的状态存储====================
#         st.session_state.messages.append({
#             'role': 'assistant',
#             'content': full_response
#         })

# user_query = ''
def streamlit_refresh_loop():
    # =============================侧栏==============================
    with st.sidebar:
        role_prompt = st.text_area(label="请输入您的角色提示语:", value="")
        connecting_internet = st.checkbox('联网')
        # tx = st.text_area(label="请输入您的指令:", value="")
        col0, col1, col2 = st.columns([2, 1, 1])
        col1.button("清空记录", on_click=on_clear_history)
        col2.button("中止回复", on_click=on_cancel_response)
        # col3.button("确认", on_click=on_confirm_response, args=[tx, role_prompt, connecting_internet])
        # add_selectbox = st.selectbox(
        #     "How would you like to be contacted?",
        #     ("Email", "Home phone", "Mobile phone")
        # )
        # add_radio = st.radio(
        #     "Choose a shipping method",
        #     ("Standard (5-15 days)", "Express (2-5 days)")
        # )

    # =======================所有chat历史的显示========================
    prompt = st.chat_input("请在这里输入您的指令")

    if 'messages' not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

    if prompt:
        # =======================user输入的显示=======================
        with st.chat_message('user'):
            st.markdown(prompt)
        # =====================user输入的状态存储======================
        st.session_state.messages.append({
            'role': 'user',
            'content': prompt
        })

        # ====================assistant输出的显示=====================
        with st.chat_message('assistant'):
            message_placeholder = st.empty()
            full_response = ''
            for res in llm_response(prompt, role_prompt, connecting_internet):
                full_response += res
                message_placeholder.markdown(full_response + '█ ')
            message_placeholder.markdown(full_response)
        # ==================assistant输出的状态存储====================
        st.session_state.messages.append({
            'role': 'assistant',
            'content': full_response
        })


if __name__ == "__main__" :
    streamlit_refresh_loop()

# import numpy as np
#
# with st.chat_message("user"):
#     st.write("Hello 👋")
#     st.line_chart(np.random.randn(30, 3))
#
# message = st.chat_message("assistant")
# message.write("Hello human")
# message.bar_chart(np.random.randn(30, 3))
#
# prompt = st.chat_input("Say something")
# if prompt:
#     st.write(f"User has sent the following prompt: {prompt}")
#
# import time
# import streamlit as st
#
# with st.status("Downloading data..."):
#     st.write("Searching for data...")
#     time.sleep(2)
#     st.write("Found URL.")
#     time.sleep(1)
#     st.write("Downloading data...")
#     time.sleep(1)
#
# st.button('Rerun')