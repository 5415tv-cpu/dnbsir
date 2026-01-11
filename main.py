"""
# 동네비서 - 모바일 최적화 키오스크 스타일
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
    }

    /* 2. 상단 헤더 (이름, 시계, 날짜) */
    .top-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 0 15px;
        margin-bottom: 30px;
    }
    .top-header .name-section {
        text-align: left;
    }
    .top-header .name {
        font-size: 24px;
        font-weight: 900;
        margin-bottom: 5px;
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
        letter-spacing: 1px;
    }
    .top-header .date {
        font-size: 14px;
        color: #AAAAAA;
    }

    /* 3. 메뉴 그리드 시스템 */
    [data-testid="stHorizontalBlock"] {
        gap: 15px !important;
        margin-bottom: 15px !important;
    }
    [data-testid="column"] {
        padding: 0 !important;
    }

    /* 4. 키오스크 카드 버튼 공통 스타일 */
    div.stButton > button {
        width: 100% !important;
        aspect-ratio: 1 / 1.1 !important; 
        border-radius: 25px !important;
        border: none !important;
        padding: 20px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        transition: transform 0.1s ease !important;
        box-shadow: 0 8px 20px rgba(0,0,0,0.5) !important;
        
        /* 글씨 스타일 */
        font-weight: 900 !important;
        text-align: center !important;
        line-height: 1.2 !important;
        white-space: pre-wrap !important;
    }
    div.stButton > button:active {
        transform: scale(0.96) !important;
    }
    div.stButton button p {
        font-size: 16px !important;
        font-weight: 500 !important;
        margin: 0 !important;
        color: inherit !important;
    }
    /* 버튼 내의 큰 텍스트(강조) 스타일링을 위한 꼼수: p 태그 내의 줄바꿈 이후 텍스트 강조 */
    /* 실제로는 버튼 텍스트 전체가 p 태그 안에 들어감 */

    /* 5. 버튼 개별 컬러 강제 적용 (순서 기반) */
    /* 첫 번째 행 왼쪽 (학과가이드) */
    div[data-testid="stVerticalBlock"] > div:nth-child(2) [data-testid="column"]:nth-child(1) button {
        background: #FFB300 !important; color: #FFFFFF !important;
    }
    
    /* 첫 번째 행 오른쪽 (북가이드) */
    div[data-testid="stVerticalBlock"] > div:nth-child(2) [data-testid="column"]:nth-child(2) button {
        background: #8E24AA !important; color: #FFFFFF !important;
    }

    /* 두 번째 행 오른쪽 (진학가이드) */
    div[data-testid="stVerticalBlock"] > div:nth-child(4) [data-testid="column"]:nth-child(2) button {
        background: #00ACC1 !important; color: #FFFFFF !important;
    }

    /* 세 번째 행 왼쪽 (심리테스트) */
    div[data-testid="stVerticalBlock"] > div:nth-child(5) [data-testid="column"]:nth-child(1) button {
        background: #D81B60 !important; color: #FFFFFF !important;
    }

    /* 세 번째 행 오른쪽 (진로레터) */
    div[data-testid="stVerticalBlock"] > div:nth-child(5) [data-testid="column"]:nth-child(2) button {
        background: #43A047 !important; color: #FFFFFF !important;
    }

    /* 6. 하단 알림바 스타일 */
    .bottom-notice {
        background: white;
        border-radius: 50px;
        padding: 10px 20px;
        display: flex;
        align-items: center;
        margin-top: 20px;
        width: 100%;
    }
    .bottom-notice .badge {
        background: #FF0000;
        color: white;
        border-radius: 20px;
        padding: 2px 12px;
        font-weight: bold;
        font-size: 14px;
        margin-right: 15px;
    }
    .bottom-notice .text {
        color: #333333;
        font-weight: 600;
        font-size: 15px;
    }

    /* 중간 로고 */
    .mid-logo-container {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        aspect-ratio: 1 / 1.1;
    }
    .mid-logo {
        text-align: center;
        font-size: 16px;
        font-weight: 700;
        letter-spacing: 5px;
        color: #FFFFFF;
        opacity: 0.8;
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
            <div class="name">오늘고등학교 😊</div>
            <div class="sub-info">서울 잠원동 6℃ 흐림 ☁️</div>
        </div>
        <div class="time-section">
            <div class="time">{now.strftime('%H : %M')}</div>
            <div class="date">{now.strftime('%Y. %m. %d')} ({['월','화','수','목','금','토','일'][now.weekday()]})</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. 메뉴 그리드 (1행)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🎓\n\n학과의 모든 정보\n학과가이드"): navigate_to("DEPT")
    with c2:
        if st.button("📚\n\n학교별 추천도서\n북가이드"): navigate_to("BOOK")

    # 3 & 4. 중간 로고 및 진학가이드 (2행)
    c3, c4 = st.columns(2)
    with c3:
        st.markdown('<div class="mid-logo-container"><div class="mid-logo">KIOSK<br>ONL:DO</div></div>', unsafe_allow_html=True)
    with c4:
        if st.button("🚀\n\n대입의 모든 정보\n진학가이드"): navigate_to("GUIDE")

    # 5. 메뉴 그리드 (3행)
    c5, c6 = st.columns(2)
    with c5:
        if st.button("☕\n\n어디로게 나를 말하는\n심리테스트"): navigate_to("TEST")
    with c6:
        if st.button("✉️\n\n교육연구들의 에너지있는\n진로레터"): navigate_to("LETTER")

    # 6. 하단 알림바
    st.markdown("""
    <div class="bottom-notice">
        <span class="badge">New!</span>
        <span class="text">진학가이드 카테고리 업데이트!</span>
    </div>
    """, unsafe_allow_html=True)

# 📄 서브 페이지 로직
else:
    st.markdown('<div style="height: 120px;"></div>', unsafe_allow_html=True)
    if st.button("🏠 홈 화면으로 돌아가기"): go_home()
    st.write("---")
    st.write(f"현재 {st.session_state.page} 페이지 준비 중입니다.")
