import streamlit as st


def render_assistant(set_page):
    st.title("AI 매장비서")
    st.info("매장비서 화면을 준비 중입니다.")

    if st.button("홈으로", use_container_width=True):
        set_page("home")
