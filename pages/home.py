import streamlit as st


def render_home(set_page):
    st.title("홈")
    st.caption("핵심 서비스로 바로 이동합니다.")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("AI 택배", use_container_width=True):
            set_page("delivery")

    with col2:
        if st.button("AI 매장비서", use_container_width=True):
            set_page("assistant")

    with col3:
        if st.button("로컬 직거래", use_container_width=True):
            set_page("local_trade")

    st.divider()
    st.write("필요한 기능이 보이지 않으면 관리자에게 문의해주세요.")
