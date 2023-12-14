import streamlit as st
from tools.llm.api_client import LLM_Client

# 包方式运行：python -m streamlit run gpu_server/llm_webui_streamlit_server.py
def main():
    llm = LLM_Client(
        history=True,  # 这里要关掉server侧llm的history，对话历史由用户session控制
        need_print=False,
        temperature=0,
    )
    prompt = st.chat_input("Say something")
    if prompt:
        st.write(f"User: {prompt}")
        st.write(f"Assistant: {llm.ask_prepare(prompt).get_answer_and_sync_print()}")

if __name__ == "__main__" :
    main()

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