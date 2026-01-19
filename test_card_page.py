import streamlit as st


def render_test_card_page():
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    st.markdown('<h1 style="color:#000000; font-weight:900;">🧪 테스트카드</h1>', unsafe_allow_html=True)

    st.markdown("""
    <div class="glass-container">
        <div style="font-size: 16px; font-weight: 900; color: #000000; margin-bottom: 10px;">테스트 결제 카드 안내</div>
        <div style="font-size: 14px; font-weight: 900; color: #000000; line-height: 1.6;">
            • 카드번호: 4111 1111 1111 1111<br>
            • 비밀번호: 12
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("테스트 결제 진행하기", use_container_width=True):
        st.session_state.page = "PAYMENT"
        st.query_params["page"] = "PAYMENT"
        st.rerun()

    if st.button("⬅️ 홈으로 돌아가기", use_container_width=True):
        st.session_state.page = "home"
        st.query_params.clear()
        st.rerun()
