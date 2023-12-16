import streamlit as st
from tools.llm.api_client import LLM_Client

import time

# 包方式运行：python -m streamlit run gpu_server/llm_webui_streamlit_server.py

@st.cache_resource  # cache_resource主要用于访问db connection等仅调用一次的全局资源
def llm_init():
    return LLM_Client(
        history=True,  # 这里要关掉server侧llm的history，对话历史由用户session控制
        need_print=False,
        temperature=0,
    )
def streamlit_refresh_loop():
    llm = llm_init()

    # =============================侧栏==============================
    with st.sidebar:
        add_selectbox = st.selectbox(
            "How would you like to be contacted?",
            ("Email", "Home phone", "Mobile phone")
        )
        add_radio = st.radio(
            "Choose a shipping method",
            ("Standard (5-15 days)", "Express (2-5 days)")
        )

    # =======================所有chat历史的显示========================
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

    if prompt := st.chat_input("请在这里输入您的指令"):
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
            llm.set_role_prompt('不论发送什么文字给你，你都直接翻译为英文，不要以"answer"这类此开头')
            llm.set_role_prompt('你正在模拟linux终端控制台')
            for res in llm.ask_prepare(prompt).get_answer_generator():
                full_response += res
                message_placeholder.markdown(full_response + '█ ')
            message_placeholder.markdown(full_response)
        # ==================assistant输出的状态存储====================
        st.session_state.messages.append({
            'role': 'assistant',
            'content': full_response
        })

    st.button("Reset", type="primary")
    if st.button('Say hello'):
        st.write('Why hello there')
    else:
        st.write('Goodbye')




    placeholder = st.empty()

    # Replace the placeholder with some text:
    placeholder.text("你正在模拟linux终端控制台")

    # Replace the text with a chart:
    placeholder.line_chart({"data": [1, 5, 2, 6]})

    # Replace the chart with several elements:
    with placeholder.container():
        st.write("This is one element")
        st.write("This is another")

    # Clear all those elements:
    placeholder.empty()




    from io import StringIO
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        # To read file as bytes:
        bytes_data = uploaded_file.getvalue()
        st.write(bytes_data)

        # # To convert to a string based IO:
        # stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        # st.write(stringio)
        #
        # # To read file as string:
        # string_data = stringio.read()
        # st.write(string_data)
        #
        # # Can be used wherever a "file-like" object is accepted:
        # dataframe = pd.read_csv(uploaded_file)
        # st.write(dataframe)

    with st.status("Downloading data...", expanded=True) as status:
        st.write("Searching for data...")
        time.sleep(2)
        st.write("Found URL.")
        time.sleep(1)
        st.write("Downloading data...")
        time.sleep(1)
        status.update(label="Download complete!", state="complete", expanded=False)

    st.button('Rerun')

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