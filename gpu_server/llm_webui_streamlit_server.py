import streamlit as st
from tools.llm.api_client import LLM_Client

# 包方式运行：python -m streamlit run gpu_server/llm_webui_streamlit_server.py

@st.cache_resource
def llm_init():
    return LLM_Client(
        history=True,  # 这里要关掉server侧llm的history，对话历史由用户session控制
        need_print=False,
        temperature=0,
    )

def streamlit_main():
    llm = llm_init()

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

    if prompt := st.chat_input("Say something"):
        st.session_state.messages.append({
            'role': 'user',
            'content': prompt
        })
        with st.chat_message('user'):
            st.markdown(prompt)

        with st.chat_message('assistant'):
            message_placeholder = st.empty()
            full_response = ''
            llm.set_role_prompt('不论发送什么文字给你，你都直接翻译为英文，不要以"answer"这类此开头')
            llm.set_role_prompt('你正在模拟linux终端控制台')
            for res in llm.ask_prepare(prompt).get_answer_generator():
                full_response += res
                message_placeholder.markdown(full_response + '█ ')
            message_placeholder.markdown(full_response)

        st.session_state.messages.append({
            'role': 'assistant',
            'content': full_response
        })

if __name__ == "__main__" :
    streamlit_main()

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