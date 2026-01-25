import streamlit as st


def render_delivery(set_page):
    st.title("AI 택배")
    st.info("배송 접수 화면을 준비 중입니다.")

    if st.button("홈으로", use_container_width=True):
        set_page("home")
