import streamlit as st


def _init_state():
    st.session_state.setdefault("page", "home")


def _set_page(name: str) -> None:
    st.session_state.page = name


def render_home():
    st.markdown(
        """
        <style>
        .section-title {
            font-size: 22px;
            font-weight: 900;
            margin-bottom: 4px;
        }
        .section-subtitle {
            font-size: 13px;
            opacity: 0.7;
            margin-bottom: 16px;
        }
        .stButton > button {
            border-radius: 16px !important;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.12) !important;
            font-weight: 900 !important;
        }
        button[data-testid="baseButton-primary"] {
            height: 110px !important;
            font-size: 20px !important;
            box-shadow: 0 12px 26px rgba(0, 0, 0, 0.16) !important;
        }
        button[data-testid="baseButton-secondary"] {
            height: 56px !important;
            font-size: 13px !important;
            box-shadow: 0 6px 14px rgba(0, 0, 0, 0.08) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">동네비서 통합 대시보드</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">핵심 서비스와 부가 메뉴를 빠르게 이동하세요.</div>', unsafe_allow_html=True)

    st.markdown("### 핵심 서비스")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🚚 AI 택배", use_container_width=True, key="card_delivery", type="primary"):
            _set_page("delivery")
    with col2:
        if st.button("🤖 AI 매장비서", use_container_width=True, key="card_assistant", type="primary"):
            _set_page("assistant")
    with col3:
        if st.button("💰 실시간 수익", use_container_width=True, key="card_settlement", type="primary"):
            _set_page("settlement")

    st.markdown("### 기타 메뉴")
    col4, col5, col6 = st.columns(3)
    with col4:
        if st.button("⚙️ 매장 관리", use_container_width=True, key="menu_store_mgmt", type="secondary"):
            _set_page("store_mgmt")
    with col5:
        if st.button("💎 프리미엄 리포트", use_container_width=True, key="menu_report", type="secondary"):
            _set_page("report")
    with col6:
        if st.button("📢 고객지원", use_container_width=True, key="menu_support", type="secondary"):
            _set_page("support")


def render_placeholder(title: str):
    st.title(title)
    st.info("해당 페이지는 준비 중입니다.")
    if st.button("홈으로", use_container_width=True):
        _set_page("home")


def render_router():
    page = st.session_state.page
    if page == "home":
        render_home()
        return

    titles = {
        "delivery": "AI 택배",
        "assistant": "AI 매장비서",
        "local_trade": "로컬 직거래",
        "report": "프리미엄 리포트",
        "settlement": "정산 센터",
        "support": "고객지원",
        "store_mgmt": "매장 관리",
    }
    render_placeholder(titles.get(page, "페이지"))


def main():
    st.set_page_config(page_title="동네비서", layout="wide")
    _init_state()
    render_router()


if __name__ == "__main__":
    main()
