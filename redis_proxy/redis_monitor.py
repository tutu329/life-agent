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

def show_llm(tab1):
    # 实时获取redis变量
    status = r.get_dict('LLM_Client status')
    # 由dict转换为dataclass
    data = from_dict(LLM_Client_Status, status)

    # 显示data
    tab1.markdown(f'【uuid】 {data.uuid}')
    tab1.markdown(f'【system prompt】 {data.system_prompt}')
    tab1.markdown(f'【role prompt】 {data.role_prompt}')
    tab1.markdown(f'【temperature】 {data.temperature}')
    tab1.markdown(f'【stops】 {data.stops}')
    tab1.markdown(f'【max new tokens】 {data.max_new_tokens}')

    last_response = data.last_response.replace("\n", " ") if data.last_response else ''
    last_response = last_response[:50]+'...' if len(last_response)>50 else last_response

    tab1.markdown(f'【上一问题】  {data.question}')
    tab1.markdown(f'【上一回复】 {last_response}')
    tab1.markdown(f'【对话历史】')
    for chat in data.history_list:
        content = chat['content'].replace("\n", " ") if chat['content'] else ''
        content = content[:50]+'...' if len(content)>50 else content
        tab1.markdown(f"{'&nbsp;' * 16}【{chat['role']}】 {content}")

def show_other(tab2):
    tab2.markdown('dd')
    tab2.markdown('hi')

def streamlit_refresh_loop():
    # 创建标签页
    tab1, tab2 = st.tabs(["LLM", "other"])

    # 主循环，每秒刷新一次数据
    while True:
        # ----------------------------------LLM----------------------------------------
        show_llm(tab1)
        show_other(tab2)

        # ----------------------------------刷新----------------------------------------
        time.sleep(1)
        st.rerun()
        # st.experimental_rerun()

if __name__ == "__main__":
    streamlit_refresh_loop()

