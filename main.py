"""
# 오늘고등학교 - 모바일 최적화 키오스크 스타일
# Version: 1.0.2 (Force Update)
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import db_manager
import time
import pwa_helper

# ==========================================
# 🎨 페이지 설정 (모바일 standalone 최적화)
# ==========================================
st.set_page_config(
    page_title="동네비서", 
    page_icon="🏘️",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# PWA 설정
pwa_helper.inject_pwa_tags()
st.markdown(pwa_helper.get_pwa_css(), unsafe_allow_html=True)

# ==========================================
# 💎 키오스크 스타일 CSS
# ==========================================
st.markdown("""
<style>
    /* 1. 글로벌 배경 - 깊은 검정색 */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #000000 !important;
        background-image: none !important;
        font-family: 'Pretendard', sans-serif !important;
        color: #FFFFFF !important;
    }

    /* 상단 영역 조정 */
    .main .block-container {
        padding-top: 30px !important;
        max-width: 500px !important; 
        margin: 0 auto !important;
    }

    /* 2. 상단 헤더 */
    .top-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 0 15px;
        margin-bottom: 20px;
    }
    .top-header .name {
        font-size: 24px;
        font-weight: 900;
        color: #FFFFFF !important;
    }
    .top-header .sub-info {
        font-size: 14px;
        color: #AAAAAA;
    }
    .top-header .time-section {
        text-align: right;
    }
    .top-header .time {
        font-size: 26px;
        font-weight: 700;
        color: #FFFFFF !important;
    }

    /* 3. 메뉴 그리드 */
    [data-testid="stHorizontalBlock"] {
        gap: 10px !important;
        margin-bottom: 10px !important;
    }

    /* 4. 카드 버튼 스타일 (백지 현상 방지) */
    .stButton button {
        width: 100% !important;
        height: 140px !important;
        border-radius: 20px !important;
        border: none !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
        padding: 10px !important;
    }
    
    /* 버튼 텍스트 강제 노출 */
    .stButton button p {
        color: #FFFFFF !important;
        font-size: 15px !important;
        font-weight: 800 !important;
        line-height: 1.3 !important;
        margin-top: 5px !important;
        opacity: 1 !important;
        visibility: visible !important;
        display: block !important;
    }

    /* 버튼 아이콘(이모지) 스타일 */
    .btn-icon {
        font-size: 32px;
        margin-bottom: 5px;
        display: block;
    }

    /* 버튼 개별 컬러 */
    div.btn-1 button { background-color: #FFB300 !important; } /* 노랑 */
    div.btn-2 button { background-color: #8E24AA !important; } /* 보라 */
    div.btn-3 button { background-color: #00ACC1 !important; } /* 하늘 */
    div.btn-4 button { background-color: #D81B60 !important; } /* 빨강 */
    div.btn-5 button { background-color: #43A047 !important; } /* 초록 */
    div.btn-6 button { background-color: #5C6BC0 !important; } /* 남색 */
    div.btn-7 button { background-color: #FFA726 !important; } /* 주황 */
    div.btn-8 button { background-color: #26A69A !important; } /* 청록 */
    div.btn-9 button { background-color: #78909C !important; } /* 회색 */
    div.btn-10 button { background-color: #66BB6A !important; } /* 연두 */

    /* 중간 로고 */
    .mid-logo-container {
        text-align: center;
        padding: 15px 0;
        color: #FFFFFF;
        font-weight: bold;
        letter-spacing: 3px;
        font-size: 14px;
        opacity: 0.7;
    }

    /* 하단 알림바 */
    .bottom-notice {
        background: white;
        border-radius: 50px;
        padding: 8px 15px;
        display: flex;
        align-items: center;
        margin-top: 15px;
    }
    .bottom-notice .badge {
        background: #FF0000;
        color: white;
        border-radius: 20px;
        padding: 2px 10px;
        font-weight: bold;
        font-size: 12px;
        margin-right: 10px;
    }
    .bottom-notice .text {
        color: #333333;
        font-size: 13px;
        font-weight: 600;
    }

    /* 스트림릿 기본 요소 제거 */
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stSidebar"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# 🚀 네비게이션 로직
if "page" not in st.session_state:
    st.session_state.page = "HOME"

def navigate_to(page_name):
    st.session_state.page = page_name
    st.rerun()

def go_home():
    st.session_state.page = "HOME"
    st.rerun()

# 🏠 [메인] 홈 화면
if st.session_state.page == "HOME":
    # 1. 상단 헤더
    now = datetime.now()
    st.markdown(f"""
    <div class="top-header">
        <div class="name-section">
            <div class="name">동네비서 😊</div>
            <div class="sub-info">서울 잠원동 6℃ 흐림 ☁️</div>
        </div>
        <div class="time-section">
            <div class="time">{now.strftime('%H : %M')}</div>
            <div class="date">{now.strftime('%Y. %m. %d')} ({['월','화','수','목','금','토','일'][now.weekday()]})</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. 메뉴 그리드 (10개 카드)
    
    # 1행
    r1_c1, r1_c2 = st.columns(2)
    with r1_c1:
        st.markdown('<div class="btn-1">', unsafe_allow_html=True)
        if st.button("🏘️\n매장 예약"): navigate_to("RESERVE")
        st.markdown('</div>', unsafe_allow_html=True)
    with r1_c2:
        st.markdown('<div class="btn-2">', unsafe_allow_html=True)
        if st.button("📦\n택배 접수"): navigate_to("DELIVERY")
        st.markdown('</div>', unsafe_allow_html=True)

    # 2행
    r2_c1, r2_c2 = st.columns(2)
    with r2_c1:
        st.markdown('<div class="btn-3">', unsafe_allow_html=True)
        if st.button("🤖\nAI 분석"): navigate_to("AI_VISION")
        st.markdown('</div>', unsafe_allow_html=True)
    with r2_c2:
        st.markdown('<div class="btn-4">', unsafe_allow_html=True)
        if st.button("🧠\n심리테스트"): navigate_to("TEST")
        st.markdown('</div>', unsafe_allow_html=True)

    # 중간 로고 영역
    st.markdown('<div class="mid-logo-container">KIOSK ONL:DO</div>', unsafe_allow_html=True)

    # 3행
    r3_c1, r3_c2 = st.columns(2)
    with r3_c1:
        st.markdown('<div class="btn-5">', unsafe_allow_html=True)
        if st.button("✉️\n진로레터"): navigate_to("LETTER")
        st.markdown('</div>', unsafe_allow_html=True)
    with r3_c2:
        st.markdown('<div class="btn-6">', unsafe_allow_html=True)
        if st.button("👥\n고객 관리"): navigate_to("CUSTOMERS")
        st.markdown('</div>', unsafe_allow_html=True)

    # 4행
    r4_c1, r4_c2 = st.columns(2)
    with r4_c1:
        st.markdown('<div class="btn-7">', unsafe_allow_html=True)
        if st.button("📢\n공지사항"): navigate_to("NOTICE")
        st.markdown('</div>', unsafe_allow_html=True)
    with r4_c2:
        st.markdown('<div class="btn-8">', unsafe_allow_html=True)
        if st.button("📖\n이용 가이드"): navigate_to("GUIDE_DOC")
        st.markdown('</div>', unsafe_allow_html=True)

    # 5행
    r5_c1, r5_c2 = st.columns(2)
    with r5_c1:
        st.markdown('<div class="btn-9">', unsafe_allow_html=True)
        if st.button("⚙️\n관리자 설정"): navigate_to("ADMIN_CONFIG")
        st.markdown('</div>', unsafe_allow_html=True)
    with r5_c2:
        st.markdown('<div class="btn-10">', unsafe_allow_html=True)
        if st.button("👤\n내 정보"): navigate_to("MY_INFO")
        st.markdown('</div>', unsafe_allow_html=True)

    # 3. 하단 알림바
    st.markdown("""
    <div class="bottom-notice">
        <span class="badge">New!</span>
        <span class="text">동네비서 시스템 업데이트 완료!</span>
    </div>
    """, unsafe_allow_html=True)

# 📄 서브 페이지 로직
else:
    st.markdown('<div style="height: 120px;"></div>', unsafe_allow_html=True)
    if st.button("🏠 홈 화면으로 돌아가기"): go_home()
    st.write("---")
    st.write(f"현재 {st.session_state.page} 페이지 준비 중입니다.")
