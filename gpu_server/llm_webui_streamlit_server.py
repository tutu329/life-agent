import streamlit as st
from tools.llm.api_client import LLM_Client

import time
import asyncio
from tools.retriever.search import Bing_Searcher

from utils.long_content_summary import long_content_summary

# 包方式运行：python -m streamlit run gpu_server/llm_webui_streamlit_server.py --server.port 7860

# 配置(必须第一个调用)
st.set_page_config(
    initial_sidebar_state="collapsed",
    page_title="Qwen-72B",
)
@st.cache_resource  # cache_resource主要用于访问db connection等仅调用一次的全局资源
def llm_init():
    return LLM_Client(
        history=True,  # 这里要关掉server侧llm的history，对话历史由用户session控制
        need_print=False,
        temperature=0,
    )

# 返回searcher及其loop
@st.cache_resource
def search_init():
    import sys, platform
    fix_streamlit_in_win = True if sys.platform.startswith('win') else False
    return Bing_Searcher.create_searcher_and_loop(fix_streamlit_in_win)   # 返回loop，主要是为了在searcher完成start后，在同一个loop中执行query_bing_and_get_results()

# asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
llm = llm_init()
searcher = search_init()

def on_clear_history():
    st.session_state.messages = []
    llm.clear_history()

def on_cancel_response():
    llm.cancel_response()

def llm_response(prompt, role_prompt, connecting_internet):
    llm.set_role_prompt(role_prompt)

    # =================================搜索并llm=================================
    if connecting_internet:
        global internet_search_result
        # =================================搜索=================================
        with st.status("Searching via internet...", expanded=True) as status:
            st.write("Searching in bing.com...")

            print('======================1=======================')
            internet_search_result = searcher.search_long_time(prompt)
            print(f'internet_search_result: {internet_search_result}')
            print('======================3=======================')
            status.update(label="Searching completed.", state="complete", expanded=False)

        # =================================llm=================================
        url_idx = 0
        found = False
        for url, content_para_list in internet_search_result:
            found = True
            url_idx += 1

            temp_llm = LLM_Client(history=False, need_print=False, temperature=0)
            content = " ".join(content_para_list)
            # prompt = f'这是网络搜索结果: "{content}", 请根据该搜索结果用中文回答用户的提问: "{prompt}"，回复要简明扼要、层次清晰、采用markdown格式。'
            gen = long_content_summary(temp_llm, content)
            # gen = temp_llm.ask_prepare(prompt).get_answer_generator()
            for chunk in gen:
                yield chunk
            yield f'\n\n出处[{url_idx}]: ' + url + '\n\n'
            # st.write(f'\n\n出处[{url_idx}]: ' + url + '\n\n')
    else:
    # =================================仅llm=================================
        gen = llm.ask_prepare(prompt).get_answer_generator()
        for chunk in gen:
            yield chunk

def streamlit_refresh_loop():
    # =============================侧栏==============================
    with st.sidebar:
        role_prompt = st.text_area(label="请输入您的角色提示语:", value="")
        # add_selectbox = st.selectbox(
        #     "How would you like to be contacted?",
        #     ("Email", "Home phone", "Mobile phone")
        # )
        # add_radio = st.radio(
        #     "Choose a shipping method",
        #     ("Standard (5-15 days)", "Express (2-5 days)")
        # )

    # =======================所有chat历史的显示========================
    col0, col1, col2, col3 = st.columns([4, 1, 1, 1])
    col1.button("Clear", on_click=on_clear_history)
    col2.button("Cancel", on_click=on_cancel_response)
    connecting_internet = col3.checkbox('联网')

    if 'messages' not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

    prompt = st.chat_input("请在这里输入您的指令")
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


    # st.button("Reset", type="primary")
    # if st.button('Say hello'):
    #     st.write('Why hello there')
    # else:
    #     st.write('Goodbye')
    #
    #
    #
    #
    # placeholder = st.empty()
    #
    # # Replace the placeholder with some text:
    # placeholder.text("你正在模拟linux终端控制台")
    #
    # # Replace the text with a chart:
    # placeholder.line_chart({"data": [1, 5, 2, 6]})
    #
    # # Replace the chart with several elements:
    # with placeholder.container():
    #     st.write("This is one element")
    #     st.write("This is another")
    #
    # # Clear all those elements:
    # placeholder.empty()
    #
    #
    #
    #
    # from io import StringIO
    # uploaded_file = st.file_uploader("Choose a file")
    # if uploaded_file is not None:
    #     # To read file as bytes:
    #     bytes_data = uploaded_file.getvalue()
    #     st.write(bytes_data)
    #
    #     # # To convert to a string based IO:
    #     # stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    #     # st.write(stringio)
    #     #
    #     # # To read file as string:
    #     # string_data = stringio.read()
    #     # st.write(string_data)
    #     #
    #     # # Can be used wherever a "file-like" object is accepted:
    #     # dataframe = pd.read_csv(uploaded_file)
    #     # st.write(dataframe)
    #
    # with st.status("Downloading data...", expanded=True) as status:
    #     st.write("Searching for data...")
    #     time.sleep(2)
    #     st.write("Found URL.")
    #     time.sleep(1)
    #     st.write("Downloading data...")
    #     time.sleep(1)
    #     status.update(label="Download complete!", state="complete", expanded=False)
    #
    # st.button('Rerun')

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