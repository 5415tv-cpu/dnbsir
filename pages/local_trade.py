import streamlit as st


def render_local_trade(set_page):
    st.title("로컬 직거래")
    st.info("로컬 직거래 화면을 준비 중입니다.")

    if st.button("홈으로", use_container_width=True):
        set_page("home")
