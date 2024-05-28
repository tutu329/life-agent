import streamlit as st

from redis_client import Redis_Client, from_dict
from tools.llm.api_client import LLM_Client_Status

st.set_page_config(
    initial_sidebar_state="collapsed",
    page_title="Life-Agent",
    layout="wide",
)

@st.cache_resource  # cache_resource主要用于访问db connection等仅调用一次的全局资源
def redis_init():
    redis_client = Redis_Client()
    return redis_client

r = redis_init()



def streamlit_refresh_loop():
    status = r.get_dict('LLM_Client status')
    data = from_dict(LLM_Client_Status, status)
    st.markdown(status)
    st.markdown(data)
    # st.rerun()

if __name__ == "__main__":
    streamlit_refresh_loop()