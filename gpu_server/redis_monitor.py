import time
import streamlit as st

from redis_client import Redis_Client, from_dict
from tools.llm.api_client import LLM_Client_Status

st.set_page_config(
    initial_sidebar_state="collapsed",
    page_title="Redis Monitor",
    layout="wide",
)

@st.cache_resource  # cache_resource主要用于访问db connection等仅调用一次的全局资源
def redis_init():
    redis_client = Redis_Client()
    return redis_client

r = redis_init()

def streamlit_refresh_loop():
    # 创建标签页
    tab1, tab2 = st.tabs(["LLM", "other"])

    # 主循环，每秒刷新一次数据
    while True:
        # ----------------------------------LLM----------------------------------------
        status = r.get_dict('LLM_Client status')
        data = from_dict(LLM_Client_Status, status)

        tab1.markdown(f'【问题】  {data.question}')
        tab1.markdown(f'【uuid】 {data.uuid}')
        tab1.markdown(f'【system prompt】 {data.system_prompt}')
        tab1.markdown(f'【role prompt】 {data.role_prompt}')
        tab1.markdown(f'【temperature】 {data.temperature}')
        tab1.markdown(f'【stops】 {data.stops}')
        tab1.markdown(f'【max new tokens】 {data.max_new_tokens}')
        last_response = data.last_response.replace("\n", " ")[:50]
        tab1.markdown(f'【上一次回复】 {last_response}...')
        tab1.markdown(f'【对话历史】')
        for chat in data.history_list:
            content = chat['content'].replace("\n", " ")[:50]
            tab1.markdown(f"{'&nbsp;'*16}【{chat['role']}】 {content}...")



        # ----------------------------------other----------------------------------------
        tab2.markdown('dd')
        tab2.markdown('hi')

        # ----------------------------------刷新----------------------------------------
        time.sleep(1)
        st.rerun()
        # st.experimental_rerun()

if __name__ == "__main__":
    streamlit_refresh_loop()