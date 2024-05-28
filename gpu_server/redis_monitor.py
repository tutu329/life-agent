import streamlit as st

st.set_page_config(
    initial_sidebar_state="collapsed",
    page_title="Life-Agent",
    layout="wide",
)



@st.cache_resource  # cache_resource主要用于访问db connection等仅调用一次的全局资源
def llm_init():
    pass

def streamlit_refresh_loop():
    st.markdown('hello')
    # st.rerun()

if __name__ == "__main__":
    streamlit_refresh_loop()