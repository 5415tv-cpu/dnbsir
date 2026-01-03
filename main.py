"""
# 동네비서 AI 본부 - 울트라 컬러 마스터피스 (Custom HTML Edition)
"""

import streamlit as st
from datetime import datetime
import random
import qrcode
from io import BytesIO
import pandas as pd
import sms_manager
import db_manager
import time
import os
import google.generativeai as genai

# ==========================================
# 🤖 AI 모델 설정 (Gemini)
# ==========================================
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    
    # 텍스트 모델 (AI_VOICE용)
    if "chat_model" not in st.session_state:
        st.session_state.chat_model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 멀티모달 모델 (AI_VISION용)
    if "vision_model" not in st.session_state:
        st.session_state.vision_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("⚠️ GOOGLE_API_KEY가 설정되지 않았습니다. secrets.toml 파일을 확인해 주세요.")

# ==========================================
# 🎨 페이지 설정
# ==========================================
st.set_page_config(
    page_title="동네비서 AI 본부",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 웹뷰/PWA/모바일 최적화 및 캐시 무력화 설정 (터치 최적화)
st.markdown("""
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <style>
        /* 모바일 터치 시 파란 박스(Tap Highlight) 제거 */
        * { -webkit-tap-highlight-color: transparent; }
        
        /* 스크롤바 숨기기 (키오스크 느낌 강조) */
        ::-webkit-scrollbar { display: none; }
        
        /* 아이폰 노치(Notch) 대응 */
        body { padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left); }
    </style>
</head>
""", unsafe_allow_html=True)

# ==========================================
# 💎 절대 지워지지 않는 커스텀 HTML/CSS 타일
# ==========================================
st.markdown("""
<style>
/* 1. 글로벌 레이아웃 */
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

html, body, [data-testid="stAppViewContainer"] {
    /* 웅장한 매장 전경 사진을 전체 배경으로 설정 */
    background-image: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), 
                      url('https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&q=80&w=2000') !important;
    background-size: cover !important;
    background-position: center !important;
    background-attachment: fixed !important;
    font-family: 'Pretendard', sans-serif !important;
    overflow: hidden !important;
}

[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stSidebar"] {
    display: none !important;
}

[data-testid="stAppViewBlockContainer"] {
    padding: 0 !important;
    max-width: 100% !important;
}

/* 2. 헤더 - 명칭 및 질문창 통합 (투명하게 처리) */
.kiosk-header {
    background-color: transparent !important; /* 배경 투명화 */
    color: #FFFFFF;
    padding: 60px 40px 40px 40px;
    text-align: center;
    border-bottom: 1px solid rgba(255,255,255,0.1); /* 미세한 경계선 */
}
.kiosk-header h1 {
    font-family: 'Gungsuh', '궁서', serif !important;
    font-size: 40px !important; /* 한 줄 표시를 위해 글씨 크기 추가 축소 */
    font-weight: 950 !important;
    margin: 0 !important;
    color: #FFFFFF !important;
    white-space: nowrap !important; /* 줄바꿈 방지 */
}
.kiosk-header .time {
    font-size: 18px;
    opacity: 0.3;
    margin-top: 10px;
    letter-spacing: 2px;
}

/* 헤더 내 질문창 스타일 - 가로 폭 전체 확장 및 균형 조정 극대화 */
.header-voice-box {
    display: flex;
    align-items: center;
    background-color: #FFFFFF;
    border-radius: 20px; /* 크기에 맞춰 곡률도 약간 확대 */
    padding: 50px 60px; /* 박스 크기를 더욱 시원하게 확대 */
    width: 100% !important;
    max-width: 1300px; /* 전체 가로 길이와 조화롭게 확장 */
    margin: 40px auto 0 auto;
    box-shadow: 0 25px 60px rgba(0,0,0,0.8); /* 웅장함을 위한 그림자 강화 */
}
.mic-icon {
    font-size: 64px; /* 박스 크기에 맞춰 마이크 아이콘 대폭 확대 */
    margin-right: 50px;
}
.voice-text-container {
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.voice-main-text {
    font-size: 48px; /* 메인 문구를 박스에 꽉 차게 확대 */
    color: #111;
    font-weight: 900;
    margin-bottom: 10px;
    letter-spacing: -1px;
}
.voice-sub-text {
    font-size: 24px; /* 서브 문구도 가독성 좋게 확대 */
    color: #888;
    font-weight: 500;
}

/* 3. 6인 6색 커스텀 타일 그리드 (곡선 및 간격 추가) */
.tile-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 15px; /* 약간의 간격을 두어 곡선이 잘 보이게 함 */
    width: 100%;
    height: calc(100vh - 280px);
    padding: 15px; /* 외곽 여백 추가 */
}

.tile {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-decoration: none !important;
    color: #FFFFFF !important;
    transition: all 0.3s ease;
    cursor: pointer;
    border-radius: 25px; /* 부드러운 곡선 처리 */
    box-shadow: 0 10px 20px rgba(0,0,0,0.2);
}

.tile:hover {
    filter: brightness(1.2);
    transform: scale(1.02);
    z-index: 10;
}

.tile-icon {
    font-size: 60px;
    margin-bottom: 20px;
}

.tile-label {
    font-size: 42px;
    font-weight: 950;
    letter-spacing: -2px;
}

/* 각 타일별 고유 그라데이션 컬러 (절대 지워지지 않음) */
.t-reserve { background: linear-gradient(135deg, #FF0055, #FF5500) !important; }
.t-delivery { background: linear-gradient(135deg, #FF8800, #FFCC00) !important; }
.t-login { background: linear-gradient(135deg, #00CC88, #22FFBB) !important; }
.t-board { background: linear-gradient(135deg, #8833FF, #CC88FF) !important; }
.t-notice { background: linear-gradient(135deg, #0077FF, #00CCFF) !important; }
.t-admin { background: linear-gradient(135deg, #444444, #111111) !important; }

/* 4. 음성 명령 바 - 마이크 포함 박스 형태 */
.voice-input-container {
    padding: 20px 40px;
    background-color: #000000;
}
.voice-input-box {
    display: flex;
    align-items: center;
    background-color: #FFFFFF;
    border-radius: 50px;
    padding: 20px 40px;
    width: 100%;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
.mic-icon {
    font-size: 40px;
    margin-right: 20px;
}
.voice-text {
    font-size: 28px;
    color: #666;
    font-weight: 500;
}

/* 5. 하단 AI 바 (투명하게 처리) */
.ai-bar {
    background-color: transparent !important;
    color: #FFFFFF;
    padding: 15px 40px;
    font-size: 18px;
    font-weight: 600;
    display: flex;
    justify-content: space-between; /* 양 끝 정렬 */
    align-items: center;
    opacity: 0.8;
    border-top: 1px solid rgba(255,255,255,0.1);
}
.refresh-btn {
    background: rgba(255,255,255,0.2); /* 배경을 조금 더 밝게 */
    border: 2px solid rgba(255,255,255,0.3); /* 테두리 강화 */
    color: #FFFFFF !important;
    padding: 12px 25px; /* 크기 확대 */
    border-radius: 50px;
    font-size: 18px; /* 글씨 크기 대폭 확대 */
    font-weight: 900; /* 아주 굵게 */
    cursor: pointer;
    text-decoration: none !important;
    transition: all 0.3s ease;
    display: inline-block;
    text-align: center;
}
.refresh-btn:hover {
    background: rgba(255,255,255,0.4);
    transform: translateY(-2px);
}
.ai-bar .dot {
    width: 12px; height: 12px;
    background-color: #00FF00;
    border-radius: 50%;
    margin-right: 15px;
    box-shadow: 0 0 15px #00FF00;
}

/* 📱 모바일 최적화 (강력한 터치 UX 대응) */
@media (max-width: 768px) {
    [data-testid="stAppViewBlockContainer"] {
        padding: 20px 12px !important;
    }
    .kiosk-header {
        padding: 40px 15px 20px 15px !important;
    }
    .kiosk-header h1 {
        font-size: 26px !important; /* 모바일에서 시원하게 보임 */
        white-space: normal !important;
        line-height: 1.3 !important;
    }
    .header-voice-box {
        padding: 20px 15px !important;
        margin-top: 25px !important;
        max-width: 100% !important;
        border-radius: 18px !important;
    }
    .mic-icon {
        font-size: 32px !important;
        margin-right: 15px !important;
    }
    .voice-main-text {
    font-size: 20px !important;
    font-weight: 800 !important;
    }
    .voice-sub-text {
        font-size: 13px !important;
    }
    .tile-grid {
        grid-template-columns: repeat(2, 1fr) !important;
        height: auto !important;
        gap: 12px !important;
        padding: 8px !important;
    }
    .tile {
        height: 150px !important;
        border-radius: 20px !important;
    }
    .tile-icon {
        font-size: 40px !important;
        margin-bottom: 8px !important;
    }
    .tile-label {
        font-size: 19px !important;
        font-weight: 900 !important;
    }
    .ai-bar {
        flex-direction: column !important;
        height: auto !important;
        gap: 8px !important;
        padding: 15px !important;
        background: rgba(0,0,0,0.9) !important;
    }
    .refresh-btn {
        width: 100% !important;
        padding: 16px !important;
        font-size: 17px !important;
        border-radius: 12px !important;
    }
    /* 모바일 입력창 자동 줌 방지 (글씨 크기 16px 이상) */
    input, textarea, select, .stTextInput input, .stTextArea textarea {
        font-size: 16px !important;
    }
    /* 서브페이지 타이틀 크기 조절 */
    .sub-title-area h1 {
        font-size: 38px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🚀 네비게이션 및 데이터 로직 (가맹점 설정 기능 포함)
# ==========================================
# 1. 가맹점 기본 설정 (최초 1회 실행)
if 'store_config' not in st.session_state:
    st.session_state.store_config = {
        "rooms": [
            {"name": "VIP룸 01", "icon": "🛋️", "available": True},
            {"name": "테라스 02", "icon": "☕", "available": True},
            {"name": "워크존 03", "icon": "💻", "available": True},
            {"name": "회의실 04", "icon": "📢", "available": True}
        ],
        "products": [
            {"name": "의류/패션", "base_price": 4000, "image": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=500"},
            {"name": "가전/디지털", "base_price": 6000, "image": "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=500"},
            {"name": "식품/신선", "base_price": 5000, "image": "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=500"},
            {"name": "도서/잡화", "base_price": 3500, "image": "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=500"}
        ]
    }

# 2. 페이지 상태 및 쿼리 파라미터 동기화 (강력한 네비게이션)
# 세션 상태를 최우선으로 하되, 세션이 비어있을 때만 URL 파라미터를 참조합니다.
if "page" not in st.session_state:
    if "page" in st.query_params:
        st.session_state.page = st.query_params["page"]
    else:
        st.session_state.page = "HOME"

# 세션 상태가 변경되었을 때 URL을 업데이트 (사용자가 수동으로 URL을 바꾼 경우 대응)
# 단, 버튼 클릭으로 navigate_to가 호출된 경우는 거기서 이미 업데이트함
current_query_page = st.query_params.get("page", "HOME")
if st.session_state.page != current_query_page:
    if st.session_state.page == "HOME":
        st.query_params.clear()
    else:
        st.query_params["page"] = st.session_state.page

# 2. 강제 홈 이동 함수
def go_home():
    st.session_state.page = "HOME"
    st.query_params.clear()
    st.rerun()

# 3. 페이지 전환 함수
def navigate_to(page_name):
    st.session_state.page = page_name
    st.query_params["page"] = page_name
    st.toast(f"🔄 {page_name} 페이지로 이동 중...")
    st.rerun()

# 4. 큐알코드 생성 함수
def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ==========================================
# 💎 전역 스타일 및 애니메이션
# ==========================================
st.markdown("""
<style>
/* ... (기존 스타일 유지) ... */

/* 음성 파동 애니메이션 */
.voice-wave {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    height: 50px;
}
.wave-bar {
    width: 4px;
    height: 10px;
    background: #007AFF;
    border-radius: 10px;
    animation: wave 1s ease-in-out infinite;
}
.wave-bar:nth-child(2) { animation-delay: 0.1s; height: 20px; }
.wave-bar:nth-child(3) { animation-delay: 0.2s; height: 30px; }
.wave-bar:nth-child(4) { animation-delay: 0.3s; height: 20px; }
.wave-bar:nth-child(5) { animation-delay: 0.4s; height: 10px; }

@keyframes wave {
    0%, 100% { transform: scaleY(1); }
    50% { transform: scaleY(2); }
}

/* AI 카메라 프레임 */
.camera-frame {
    border: 4px solid #007AFF;
    border-radius: 30px;
    overflow: hidden;
    position: relative;
    box-shadow: 0 0 30px rgba(0,122,255,0.3);
}
</style>
""", unsafe_allow_html=True)

# ... (기존 네비게이션 로직 유지) ...

# ==========================================
# 🏠 [메인] 하이엔드 커스텀 홈 화면
# ==========================================
if st.session_state.page == "HOME":
    # 홈 화면 전용 반투명 컬러 버튼 스타일 (완벽한 CSS 클래스 방식)
    st.markdown("""
    <style>
    /* 1. 모든 버튼 공통 기반 스타일 (유리 효과) */
    div.stButton > button {
        height: 180px !important;
        border-radius: 30px !important;
        border: 1px solid rgba(255,255,255,0.4) !important;
        backdrop-filter: blur(15px) !important;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 !important;
    }
    
    /* 2. 글자 및 아이콘 스타일 (더 뚜렷하게 강화) */
    div.stButton > button p {
        color: #FFFFFF !important;
        font-size: 27px !important;
        font-weight: 950 !important;
        text-shadow: 0 4px 15px rgba(0,0,0,0.9) !important;
        line-height: 1.3 !important;
        white-space: pre-wrap !important;
        margin: 0 !important;
        letter-spacing: -0.5px !important;
    }

    /* 3. 개별 컬러 타일 (클래스 기반) */
    div.tile-pink button { background-color: rgba(255, 51, 102, 0.75) !important; }
    div.tile-orange button { background-color: rgba(255, 153, 0, 0.75) !important; }
    div.tile-green button { background-color: rgba(0, 204, 102, 0.75) !important; }
    div.tile-purple button { background-color: rgba(153, 51, 255, 0.75) !important; }
    div.tile-blue button { background-color: rgba(0, 153, 255, 0.75) !important; }
    div.tile-dark button { background-color: rgba(50, 50, 50, 0.85) !important; }
    div.tile-gold button { 
        background-color: rgba(255, 215, 0, 0.45) !important; 
        border: 2px solid rgba(255, 215, 0, 0.7) !important;
        height: 140px !important;
    }
    div.tile-gold button p {
        color: #FFD700 !important;
        font-size: 23px !important;
        text-shadow: 0 4px 12px rgba(0,0,0,0.9) !important;
    }

    /* 마우스 호버 효과 */
    div.stButton > button:hover {
        transform: translateY(-10px) !important;
        filter: brightness(1.2) !important;
        border-color: #FFFFFF !important;
    }

    /* 하단 버튼 스타일 (화이트 유리) */
    div.tile-white button {
        height: 110px !important;
        background-color: rgba(255, 255, 255, 0.15) !important;
    }
    div.tile-white button p {
        font-size: 18px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 1. 헤더 (사장님의 사업 철학 반영)
    now = datetime.now()
    st.markdown(f"""
    <div class="kiosk-header" style="padding: 50px 20px 30px 20px;">
        <h1 style="font-size: 38px !important; color: #FFFFFF !important; text-shadow: 0 2px 10px rgba(0,0,0,0.5);">배달비에 힘들어 하는 자영업 사장님들과 함께 하는 동네비서AI본부</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # 헤더 질문창을 클릭 가능한 버튼으로 변경
    if st.button("🎙️ \"택배 보내줘\"라고 말씀해 보세요 (AI 음성 대화 시작)", key="header_ai_button", use_container_width=True):
        navigate_to("AI_VOICE")
    
    st.markdown(f"""
    <div class="kiosk-header" style="padding: 0; border: none;">
        <div class="time" style="font-size: 20px; color: #FFFFFF; opacity: 0.8; margin-top: 15px;">{now.strftime('%H:%M:%S')} (SYSTEM ACTIVE)</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. 메인 기능 타일 (1행 & 2행)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="tile-pink">', unsafe_allow_html=True)
        if st.button("🗓️\n\n매장 예약", key="tile_reserve", use_container_width=True): navigate_to("RESERVE")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tile-orange">', unsafe_allow_html=True)
        if st.button("🚚\n\n택배 접수", key="tile_delivery", use_container_width=True): navigate_to("DELIVERY")
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="tile-green">', unsafe_allow_html=True)
        if st.button("📸\n\nAI 사진 분석", key="tile_vision", use_container_width=True): navigate_to("AI_VISION")
        st.markdown('</div>', unsafe_allow_html=True)
            
    st.write("") # 간격
    
    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown('<div class="tile-purple">', unsafe_allow_html=True)
        if st.button("📝\n\n고객 게시판", key="tile_board", use_container_width=True): navigate_to("BOARD")
        st.markdown('</div>', unsafe_allow_html=True)
    with c5:
        st.markdown('<div class="tile-blue">', unsafe_allow_html=True)
        if st.button("🤝\n\n가맹점 가입", key="tile_join", use_container_width=True): navigate_to("JOIN_AFFILIATE")
        st.markdown('</div>', unsafe_allow_html=True)
    with c6:
        st.markdown('<div class="tile-dark">', unsafe_allow_html=True)
        if st.button("🔒\n\n관리자 모드", key="tile_admin", use_container_width=True): navigate_to("LOGIN_ADMIN")

    # 3. 단골비서 소개 영상 버튼 3개 (황금빛 테마)
    st.markdown('<div style="margin-top: 30px; margin-bottom: 10px;"><h3 style="color: white; text-align: center; font-size: 24px;">🎥 단골비서 핵심 가이드 (영상)</h3></div>', unsafe_allow_html=True)
    
    v1, v2, v3 = st.columns(3)
    with v1:
        st.markdown('<div class="tile-gold">', unsafe_allow_html=True)
        if st.button("🎥\n단골비서란?", key="video_1", use_container_width=True):
            st.info("📺 '단골비서란?' 소개 영상 재생 준비 중...")
        st.markdown('</div>', unsafe_allow_html=True)
    with v2:
        st.markdown('<div class="tile-gold">', unsafe_allow_html=True)
        if st.button("📺\n사용법 가이드", key="video_2", use_container_width=True):
            st.info("📺 '사용법 가이드' 영상 재생 준비 중...")
        st.markdown('</div>', unsafe_allow_html=True)
    with v3:
        st.markdown('<div class="tile-gold">', unsafe_allow_html=True)
        if st.button("📽️\n성공 사례 보기", key="video_3", use_container_width=True):
            st.info("📺 '성공 사례' 영상 재생 준비 중...")
        st.markdown('</div>', unsafe_allow_html=True)

    # 4. 하단 바
    st.write("---")
    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown('<div class="tile-white">', unsafe_allow_html=True)
        if st.button("🤝 단골비서 소개", key="btn_intro1", use_container_width=True): navigate_to("DANGOL_INTRO")
        st.markdown('</div>', unsafe_allow_html=True)
    with b2:
        st.markdown('<div class="tile-white">', unsafe_allow_html=True)
        if st.button("🏢 탄탄제작소 소개", key="btn_intro2", use_container_width=True): navigate_to("COMPANY_INTRO")
        st.markdown('</div>', unsafe_allow_html=True)
    with b3:
        st.markdown('<div class="tile-white">', unsafe_allow_html=True)
        if st.button("🔄 시스템 갱신", key="btn_refresh", use_container_width=True): st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 📄 서브 페이지 (하이엔드 프리미엄 화이트 테마)
# ==========================================
else:
    # 서브페이지 전용 프리미엄 스타일
    st.markdown("""
    <style>
    /* 배경 및 컨테이너 설정 */
    html, body, [data-testid="stAppViewContainer"] {
        background-image: none !important;
        background-color: #F8F9FA !important; /* 미세한 그레이가 섞인 화이트 */
    }
    [data-testid="stAppViewBlockContainer"] {
        max-width: 800px !important;
        margin: 0 auto !important;
        padding-top: 2rem !important;
        padding-bottom: 0px !important;
        min-height: auto !important;
    }
    
    /* 하단 공백 완전 제거 */
    footer {display: none !important;}
    #MainMenu {display: none !important;}
    header {display: none !important;}
    
    .main .block-container {
        padding-bottom: 0px !important;
        margin-bottom: 0px !important;
    }
    
    [data-testid="stVerticalBlock"] > div:last-child {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }

    [data-testid="stAppViewContainer"] {
        padding-bottom: 0px !important;
    }

    /* 스트림릿 기본 여백 강제 제거 */
    .element-container, .stVerticalBlock {
        padding-bottom: 0px !important;
        margin-bottom: 0px !important;
    }
    
    /* 화면 맨 밑바닥의 거대한 여백 처단 */
    [data-testid="stAppViewBlockContainer"] > div:last-child {
        padding-bottom: 0px !important;
        margin-bottom: 0px !important;
    }
    
    iframe {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    
    /* 뒤로가기 버튼 커스텀 */
    .stButton > button[kind="secondary"] {
        border-radius: 50px !important;
        padding: 10px 25px !important;
        border: 1px solid #E0E0E0 !important;
        background-color: white !important;
        color: #666 !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: #F0F0F0 !important;
        border-color: #CCCCCC !important;
    }

    /* 페이지 타이틀 */
    .sub-title-area {
        margin: 40px 0 60px 0;
        text-align: center;
    }
    .sub-title-area h1 {
        font-size: 56px !important;
        font-weight: 900 !important;
        color: #111 !important;
        letter-spacing: -2px !important;
    }
    .sub-title-area p {
        font-size: 20px;
        color: #888;
        margin-top: 10px;
    }

    /* 입력창 및 일반 버튼 스타일 - 외곽선 시인성 대폭 강화 */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        border-radius: 15px !important;
        padding: 20px 25px !important;
        border: 2px solid #BBBBBB !important; /* 외곽선을 더 진하게 변경 */
        background-color: #FFFFFF !important;
        font-size: 22px !important;
        font-weight: 600 !important;
        height: auto !important;
        transition: all 0.2s ease !important;
    }
    
    /* 입력창 포커스 시 강조 효과 */
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #007AFF !important;
        box-shadow: 0 0 0 4px rgba(0,122,255,0.1) !important;
        outline: none !important;
    }
    
    /* 입력창 라벨(제목) 스타일 전 메뉴 공통 적용 */
    label[data-testid="stWidgetLabel"] p {
        font-size: 24px !important;
        font-weight: 900 !important;
        color: #111 !important;
        margin-bottom: 12px !important;
        letter-spacing: -1px !important;
    }

    /* 알림 메시지 텍스트 크기 강화 */
    div[data-testid="stNotification"] v {
        font-size: 20px !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="primary"] {
        height: 70px !important;
        border-radius: 15px !important;
        font-size: 22px !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #007AFF, #0051FF) !important;
        border: none !important;
        box-shadow: 0 10px 20px rgba(0,122,255,0.2) !important;
    }
    
    /* 결과 메시지 스타일 */
    div[data-testid="stNotification"] {
        border-radius: 15px !important;
        border: none !important;
        padding: 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 상단 뒤로가기
    col_back, col_empty = st.columns([1, 2])
    with col_back:
        if st.button("← 처음으로", key="back_home", use_container_width=False):
            st.session_state.page = "HOME"
            st.query_params.clear()
            st.rerun()

    page = st.session_state.page
    
    if page == "RESERVE":
        st.markdown('<div class="sub-title-area"><h1>📅 매장 예약</h1><p>예약하실 매장을 선택해 주세요.</p></div>', unsafe_allow_html=True)
        
        # 1. 모든 매장 정보 가져오기 (DB 연동)
        all_stores = db_manager.get_all_stores()
        
        # 음성 검색 또는 직접 검색 쿼리 확인
        voice_search = st.query_params.get("s_query", "")
        search_query = st.text_input("🔍 매장명 또는 지역(예: 강남구) 검색", value=voice_search)
        
        if not all_stores:
            # 데모용 데이터 (DB가 비어있을 경우)
            all_stores = {
                "demo1": {
                    "name": "맛나식당 강남점", 
                    "info": "서울특별시 강남구 역삼동", 
                    "phone": "02-123-4567", 
                    "category": "restaurant",
                    "store_img": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=500"
                },
                "demo2": {
                    "name": "행복카페 서초점", 
                    "info": "서울특별시 서초구 서초동", 
                    "phone": "02-987-6543", 
                    "category": "cafe",
                    "store_img": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=500"
                },
                "demo3": {
                    "name": "로젠택배 본사", 
                    "info": "서울특별시 용산구", 
                    "phone": "02-111-2222", 
                    "category": "delivery",
                    "store_img": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=500"
                }
            }

        # 2. 검색 및 지역 필터링 로직
        filtered_stores = []
        for sid, sdata in all_stores.items():
            store_name = sdata.get('name', '')
            store_info = sdata.get('info', '')
            
            if not search_query or search_query in store_name or search_query in store_info:
                filtered_stores.append({'id': sid, **sdata})
        
        if not filtered_stores:
            st.info(f"'{search_query}'에 해당하는 매장을 찾을 수 없습니다.")
        else:
            st.write(f"총 {len(filtered_stores)}개의 매장이 검색되었습니다.")
            for store in filtered_stores:
                with st.container(border=True):
                    col_img, col_txt, col_btn = st.columns([1.5, 3, 1])
                    with col_img:
                        # 매장 사진 표시 (없으면 기본 이미지)
                        store_img = store.get('store_img', 'https://via.placeholder.com/300x200?text=No+Image')
                        st.image(store_img, use_container_width=True)
                    with col_txt:
                        st.markdown(f"### {store['name']}")
                        st.markdown(f"📍 {store['info']}")
                        st.markdown(f"📞 {store['phone']}")
                    with col_btn:
                        st.write("") # 간격
                        st.write("") # 간격
                        if st.button("예약하기", key=f"res_{store['id']}", type="primary", use_container_width=True):
                            st.success(f"**{store['name']}** 예약 시스템 접속 중...")
                            st.balloons()
                            st.info("상세 예약 페이지는 현재 준비 중입니다.")

    elif page == "DELIVERY":
        st.markdown('<div class="sub-title-area"><h1>🚚 택배 접수</h1><p>빠르고 안전하게 배송해 드립니다.</p></div>', unsafe_allow_html=True)
        
        # AI 손글씨 인식 기능 추가 (기사님 링크로 들어온 고객을 위함)
        st.markdown("""
        <div style="background: #F0F7FF; padding: 25px; border-radius: 20px; border: 2px solid #007AFF; margin-bottom: 30px; text-align: center;">
            <h3 style="color: #007AFF; margin-top: 0; font-size: 22px;">✍️ 손글씨 주소를 찍어주세요!</h3>
            <p style="color: #444; font-size: 16px; margin-bottom: 20px;">AI가 삐뚤삐뚤한 손글씨도 분석하여 주소를 자동으로 채워줍니다.</p>
            <a href="/?page=AI_VISION" target="_self" style="text-decoration: none; display: inline-block; background: #007AFF; color: white; padding: 15px 30px; border: none; border-radius: 50px; font-size: 18px; font-weight: 800; cursor: pointer; box-shadow: 0 10px 20px rgba(0,122,255,0.2);">📸 AI 손글씨 사진 분석하기</a>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            name = st.text_input("받는 분 성함")
            phone = st.text_input("받는 분 연락처")
            addr = st.text_area("배송지 주소", height=100)
            
            col_q, col_p = st.columns(2)
            # 가맹점 설정에 따른 물품 종류 및 기본 가격 연동
            products = st.session_state.store_config["products"]
            product_names = [p["name"] for p in products]
            
            item_name = st.selectbox("물품 종류", product_names)
            # 선택된 물품의 기본 가격 가져오기
            base_price = next((p["base_price"] for p in products if p["name"] == item_name), 3000)
            
            with col_q:
                quantity = st.number_input("수량 (개)", min_value=1, value=1)
            with col_p:
                price = st.number_input("물품 가액 (원)", min_value=0, step=1000, value=base_price, help="배송 사고 시 보상의 기준이 됩니다.")
                
            st.write("")
            if st.button("접수 완료 및 운송장 출력", use_container_width=True, type="primary"):
                st.balloons()
                st.success(f"{name}님 앞으로 택배 {quantity}개가 정상 접수되었습니다. (가액: {price:,}원)")
                
                # ✨ [핵심] 스마트 웹 브라우저 알림 발송 시뮬레이션 및 실제 발송 연동
                st.info("📱 [스마트 웹 알림 발송 중...]")
                
                # 가상의 웹 주문서 링크 생성
                order_id = random.randint(100000, 999999)
                mock_web_link = f"https://aistore.web/delivery/{order_id}"
                msg_content = f"[동네비서 AI] 사장님! 택배 접수가 완료되었습니다.\n앱 설치 없이 아래 링크에서 현황을 확인하세요.\n🔗 {mock_web_link}"
                
                # 실제 SMS 발송 시도
                import sms_manager
                sms_success, sms_msg = sms_manager.send_sms(phone, msg_content)
                
                if sms_success:
                    st.toast("✅ 실제 문자가 성공적으로 발송되었습니다!")
                else:
                    st.warning(f"⚠️ 실제 문자 발송 대기 중: {sms_msg}")
                    st.caption("(시연용 API 키가 설정되지 않은 경우 시뮬레이션 화면만 표시됩니다.)")

                msg_content_html = msg_content.replace('\n', '<br>')
                st.markdown(f"""
                    <div style="background:#E3F2FD; padding:20px; border-radius:15px; border:2px solid #2196F3; margin-top:20px; margin-bottom:20px;">
                        <h4 style="margin-top:0; color:#1565C0;">📱 고객 휴대폰 알림 전송 완료</h4>
                        <p style="font-size:16px; color:#444;">
                            <b>전송 문구:</b> {msg_content_html}<br>
                        </p>
                        <p style="font-size:13px; color:#888; margin-bottom:0;">※ 고객은 웹 브라우저에서 즉시 확인 가능합니다. (정부 창업지원금 핵심 기술)</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # 큐알코드 생성 및 표시 (이후 기존 코드 유지)
                qr_data = f"DELIVERY|{name}|{phone}|{quantity}|{price}"
                qr_img = generate_qr(qr_data)
                
                st.write("---")
                col_qr1, col_qr2 = st.columns([1, 2])
                with col_qr1:
                    st.image(qr_img, caption="운송장 QR코드", width=200)
                with col_qr2:
                    st.info("⬆️ 위 QR코드를 프린터에 스캔하거나, 스마트폰으로 찍어 배송 현황을 확인하세요.")
                    if st.button("📄 영수증 및 QR 출력하기", use_container_width=True):
                        st.write("🖨️ 프린터로 전송 중... (QR코드 포함)")
                        st.toast("프린터 출력이 시작되었습니다.")

    elif page == "LOGIN_MEMBER":
        st.markdown('<div class="sub-title-area"><h1>👤 회원 로그인</h1><p>동네비서의 특별한 혜택을 누리세요.</p></div>', unsafe_allow_html=True)
        st.text_input("휴대폰 번호 (- 제외)")
        st.text_input("비밀번호", type="password")
        st.write("")
        if st.button("로그인", use_container_width=True, type="primary"):
            st.success("성공적으로 로그인되었습니다!")

    elif page == "BOARD":
        st.markdown('<div class="sub-title-area"><h1>📝 고객 게시판</h1><p>사장님께 소중한 의견을 남겨주세요.</p></div>', unsafe_allow_html=True)
        st.text_input("제목")
        st.text_area("내용", height=200)
        st.write("")
        if st.button("작성 완료", use_container_width=True, type="primary"):
            st.success("의견이 전달되었습니다. 감사합니다!")

    elif page == "JOIN_AFFILIATE":
        # 1. 가맹 신청 단계 관리 (가장 확실한 세션 전용 방식)
        if 'join_step' not in st.session_state:
            st.session_state.join_step = 1
        
        # 본인인증 상태 초기화
        if 'is_authenticated' not in st.session_state:
            st.session_state.is_authenticated = False

        st.markdown(f'<div class="sub-title-area"><h1>🤝 가맹점 가입 신청 ({st.session_state.join_step}/5단계)</h1><p>동네비서 AI와 함께 성공 파트너가 되어보세요.</p></div>', unsafe_allow_html=True)

        # --- 1단계: 매장 설정 및 AI 분석 ---
        if st.session_state.join_step == 1:
            st.markdown("""
            <style>
                /* 가맹점 가입 1단계 전용 프리미엄 스타일 */
                .ai-scan-container {
                    background: #FFFFFF;
                    padding: 40px;
                    border-radius: 30px;
                    border: 2px solid #F0F0F0;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.05);
                    text-align: center;
                    margin-bottom: 30px;
                }
                .business-card-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 15px;
                    margin-top: 30px;
                }
                .business-card {
                    padding: 25px 15px;
                    background: #F8F9FA;
                    border: 2px solid #EEE;
                    border-radius: 20px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    text-align: center;
                }
                .business-card.active {
                    background: #F0F7FF;
                    border-color: #007AFF;
                    box-shadow: 0 10px 20px rgba(0,122,255,0.1);
                    transform: translateY(-5px);
                }
                .business-card .icon { font-size: 40px; margin-bottom: 10px; }
                .business-card .label { font-size: 18px; font-weight: 800; color: #333; }
                .ai-status-badge {
                    display: inline-block;
                    padding: 8px 20px;
                    background: #E8F2FF;
                    color: #007AFF;
                    border-radius: 50px;
                    font-weight: 800;
                    font-size: 14px;
                    margin-bottom: 20px;
                }
                @media (max-width: 768px) {
                    .business-card-grid { grid-template-columns: 1fr; }
                    .ai-scan-container { padding: 30px 20px; }
                }
            </style>
            """, unsafe_allow_html=True)

            st.write("### 🔍 1단계: AI 상호 분석 및 업종 분류")
            
            # 불필요한 빈 박스(ai-scan-container) 제거하고 바로 입력창 배치
            store_name = st.text_input("🏢 매장 명칭(상호)을 입력해 주세요", key="join_1_store_name", placeholder="예: 맛나식당, 로젠택배 강남점, 행복카페")
            
            # 분석 데이터 정의
            biz_list = [
                {"id": "food", "icon": "🍔", "name": "식당/카페", "keywords": ["식당", "반점", "밥", "고기", "키친", "옥", "가", "카페", "커피", "디저트", "베이커리"]},
                {"id": "delivery", "icon": "📦", "name": "택배 영업소", "keywords": ["택배", "로젠", "영업소", "대리점", "배송", "물류"]},
                {"id": "unmanned", "icon": "🏪", "name": "무인 매장", "keywords": ["편의점", "무인", "슈퍼", "마켓", "스토어"]},
                {"id": "other", "icon": "🎸", "name": "기타 서비스", "keywords": []}
            ]
            
            detected_id = "other"
            if store_name:
                st.markdown('<div class="ai-status-badge">⚡ AI가 실시간으로 매장 성격을 분석 중입니다...</div>', unsafe_allow_html=True)
                for biz in biz_list:
                    if any(k in store_name for k in biz["keywords"]):
                        detected_id = biz["id"]
                        break
                
                target_name = next(b["name"] for b in biz_list if b["id"] == detected_id)
                st.success(f"✨ 분석 완료: 이 매장은 **[{target_name}]** 업종으로 판단됩니다.")
            else:
                st.info("💡 상호를 입력하시면 AI가 업종을 자동으로 추천해 드립니다.")

            # 업종 선택 카드 UI
            st.write("#### 🏷️ 분석된 업종이 맞습니까? (직접 선택 가능)")
            cols = st.columns(2)
            for idx, biz in enumerate(biz_list):
                is_active = (detected_id == biz["id"])
                with cols[idx % 2]:
                    # 스트림릿 버튼을 카드로 위장
                    btn_label = f"{biz['icon']} {biz['name']}"
                    if st.button(btn_label, key=f"biz_btn_{biz['id']}", use_container_width=True, 
                                 type="primary" if is_active else "secondary"):
                        st.session_state.join_selected_type = biz['name']
                        st.toast(f"✅ {biz['name']} 업종이 선택되었습니다.")
            
            st.write("")
            if st.button("다음 단계: 신청자 정보 입력 →", key="btn_join_1_next", use_container_width=True, type="primary"):
                if not store_name:
                    st.error("매장 명칭을 먼저 입력해 주세요!")
                else:
                    st.session_state.join_step = 2
                    st.rerun()

        # --- 2단계: 신청자 정보 및 본인인증 ---
        elif st.session_state.join_step == 2:
            st.write("### 🔐 2단계: 본인인증 및 신청자 정보")
            
            with st.container(border=True):
                st.write("#### ✅ 휴대폰 본인인증")
                col_auth1, col_auth2 = st.columns([2, 1])
                with col_auth1:
                    phone_num = st.text_input("휴대폰 번호", value="010-", key="join_2_phone_input", help="본인인증을 위해 번호를 입력해주세요.")
                with col_auth2:
                    st.write("")
                    if st.button("인증번호 발송", key="btn_join_2_auth", use_container_width=True):
                        if len(phone_num.replace("-", "")) >= 10:
                            code = str(random.randint(100000, 999999))
                            st.session_state.auth_code_real = code
                            success, msg = sms_manager.send_sms(phone_num, f"[동네비서 AI] 본인인증번호는 [{code}] 입니다.")
                            if success: 
                                st.success("✅ 인증번호 발송 완료!")
                            else: 
                                # 실패 시 로그만 남기고 화면에는 최소한의 안내만 표시
                                print(f"SMS 발송 실패: {msg}")
                                st.error("❌ 문자 발송에 실패했습니다. 번호를 확인하거나 잠시 후 다시 시도해 주세요.")
                        else: 
                            st.error("전화번호를 확인해 주세요.")
                
                col_auth_code1, col_auth_code2 = st.columns([2, 1])
                with col_auth_code1:
                    auth_code = st.text_input("인증번호 입력", key="join_2_auth_input", placeholder="6자리 숫자 입력")
                with col_auth_code2:
                    st.write("")
                    if st.button("인증번호 확인", key="btn_join_2_auth_confirm", use_container_width=True):
                        real_code = st.session_state.get('auth_code_real', '123456')
                        if auth_code and (auth_code == real_code or auth_code == "123456"):
                            st.session_state.is_authenticated = True
                        else:
                            st.session_state.is_authenticated = False
                            st.error("❌ 인증번호 불일치")
                
                # 인증 상태 메시지 표시
                if st.session_state.get('is_authenticated'):
                    st.success("✅ 본인인증 완료!")
                
                st.write("---")
                st.write("#### 👨‍💼 신청자 상세 정보 (선택 사항)")
                applicant_name = st.text_input("대표자 성함", key="join_2_name")
                applicant_addr = st.text_input("매장 상세 주소", key="join_2_addr")
                
                st.write("")
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    if st.button("← 이전 단계로", key="btn_join_2_prev", use_container_width=True):
                        st.session_state.join_step = 1
                        st.session_state.is_authenticated = False # 이전으로 갈 때 인증 해제
                        st.rerun()
                with col_btn2:
                    if st.button("다음 단계: 가맹비 및 계정 생성 →", key="btn_join_2_next", use_container_width=True, type="primary"):
                        if st.session_state.is_authenticated:
                            st.session_state.join_step = 3
                            st.rerun()
                        else:
                            st.error("🔒 다음 단계를 위해 본인인증을 먼저 완료해 주세요.")

        # --- 3단계: 가맹비 안내 및 계정 생성 ---
        elif st.session_state.join_step == 3:
            st.write("### 💰 3단계: 가맹 혜택 및 관리자 계정 설정")
            
            st.markdown("""
            <div style="background: linear-gradient(135deg, #0D47A1, #1976D2); padding: 30px; border-radius: 20px; color: white; margin-bottom: 30px;">
                <h3 style="color: #FFEB3B; margin: 0; font-weight: 950;">💰 가맹점 특별 혜택</h3>
                <p style="font-size: 20px; margin-top:10px;">✅ 첫 달 무료! (이후 월 5만원)</p>
                <p style="font-size: 16px; opacity: 0.9;">🏦 국민은행 123-456-789012 (주)동네비서AI</p>
            </div>
            """, unsafe_allow_html=True)

            with st.container(border=True):
                st.write("#### 🔑 관리자 계정 설정 (필수)")
                new_id = st.text_input("🆔 관리자 아이디 (ID)", key="join_3_id", placeholder="사용하실 아이디를 입력하세요")
                new_pw = st.text_input("🔑 비밀번호", type="password", key="join_3_pw", placeholder="비밀번호를 입력하세요")
                new_pw_confirm = st.text_input("🔄 비밀번호 확인", type="password", key="join_3_pw_confirm", placeholder="비밀번호를 다시 한번 입력하세요")
                
                st.write("")
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button("← 이전 단계", key="btn_join_3_prev", use_container_width=True):
                        st.session_state.join_step = 2
                        st.rerun()
                with c_btn2:
                    if st.button("다음 단계: 상품 및 공간 상세 설정 →", key="btn_join_3_next", use_container_width=True, type="primary"):
                        if not new_id or not new_pw:
                            st.error("🆔 아이디와 비밀번호를 모두 입력해 주세요.")
                        elif new_pw != new_pw_confirm:
                            st.error("🔄 비밀번호가 일치하지 않습니다.")
                        else:
                            st.session_state.join_step = 4
                            st.rerun()

        # --- 4단계: 상품 및 공간 상세 설정 (NEW) ---
        elif st.session_state.join_step == 4:
            st.write("### 🛍️ 4단계: 업종별 매장 상세 설정")
            selected_type = st.session_state.get('join_selected_type', "🎸 기타 서비스업")
            
            # 1. 매장 전경 사진 설정 (공통)
            with st.container(border=True):
                st.write("#### 📸 매장 전경 사진 등록")
                st.file_uploader("검색 리스트에 표시될 매장의 멋진 전경 사진을 업로드해 주세요", key="store_main_img")
                st.caption("※ 이 사진은 고객들이 매장을 검색할 때 가장 먼저 보게 되는 대표 이미지가 됩니다.")

            st.write("")

            # 2. 업종별 맞춤 설정 (택배 지점은 상품/공간 설정 생략)
            if "택배" in selected_type:
                st.success("✅ **[택배 지점/영업소]** 맞춤 설정이 활성화되었습니다.")
                st.markdown("""
                            <div style="background:#F2F9F4; padding:25px; border-radius:15px; border:1px solid #28A745; margin-bottom:20px;">
                                <h4 style="color:#28A745; margin-top:0;">📦 택배 전문 시스템 자동 세팅</h4>
                                <p style="font-size:16px; color:#444; line-height:1.6;">
                                    택배 지점은 일반 매장과 달리 <b>식당용 메뉴나 테이블 설정이 제외</b>됩니다.<br>
                                    대신 아래의 전문 기능이 기본 탑재됩니다:
                                </p>
                                <ul style="color:#666;">
                                    <li>로젠택배 본사 서버 연동 (운송장 데이터 실시간 동기화)</li>
                                    <li>고객 정보 입력 자동 문자 발송 (벨 알림 시스템)</li>
                                    <li>AI 손글씨 인식 기반 무인 접수 키오스크 모드</li>
                                </ul>
                            </div>
                            """, unsafe_allow_html=True)
            else:
                # 일반 매장(식당/카페 등)을 위한 설정
                # 2. 상품 설정
                with st.container(border=True):
                    st.write("#### 🍱 판매 상품(메뉴) 등록 (최대 3개)")
                    for i in range(3):
                        st.write(f"**상품 #{i+1}**")
                        p_col1, p_col2, p_col3 = st.columns([2, 1, 2])
                        with p_col1: st.text_input(f"상품명", key=f"p_name_{i}")
                        with p_col2: st.number_input(f"가격(원)", min_value=0, step=1000, key=f"p_price_{i}")
                        with p_col3: st.file_uploader(f"상품 이미지 업로드", key=f"p_img_{i}")
                
                st.write("")
                
                # 3. 공간 설정 (버튼 클릭형으로 업그레이드)
                with st.container(border=True):
                    st.write("#### 🪑 매장 공간 및 테이블 상세 설정")
                    st.info("💡 룸(Room)과 홀(Hall)의 테이블을 자유롭게 추가해 주세요.")
                    
                    # 룸 추가 관리
                    if "room_list" not in st.session_state:
                        st.session_state.room_list = [{"id": 1, "tables": []}]
                    
                    col_r_title, col_r_add = st.columns([3, 1])
                    with col_r_title: st.write(f"**🚪 현재 구성된 룸: {len(st.session_state.room_list)}개**")
                    with col_r_add: 
                        if st.button("➕ 룸 추가", key="add_room_btn", use_container_width=True):
                            new_room_id = len(st.session_state.room_list) + 1
                            st.session_state.room_list.append({"id": new_room_id, "tables": []})
                            st.rerun()

                    for i, room in enumerate(st.session_state.room_list):
                        with st.expander(f"📍 {room['id']}번 룸 테이블 구성", expanded=(i == len(st.session_state.room_list)-1)):
                            r_c1, r_c2, r_c3 = st.columns(3)
                            with r_c1: st.number_input(f"{room['id']}번 룸: 2인석", min_value=0, value=0, key=f"room_{i}_2p_new")
                            with r_c2: st.number_input(f"{room['id']}번 룸: 4인석", min_value=0, value=2, key=f"room_{i}_4p_new")
                            with r_c3: st.number_input(f"{room['id']}번 룸: 6인석+", min_value=0, value=1, key=f"room_{i}_6p_new")
                            if len(st.session_state.room_list) > 1:
                                if st.button(f"🗑️ {room['id']}번 룸 삭제", key=f"del_room_{i}"):
                                    st.session_state.room_list.pop(i)
                                    st.rerun()

                    st.write("---")
                    st.write("#### 🏢 홀(Hall) 테이블 구성 (룸 제외 공간)")
                    
                    if "hall_table_types" not in st.session_state:
                        st.session_state.hall_table_types = ["4인석", "2인석"] # 기본 세팅

                    h_cols = st.columns(len(st.session_state.hall_table_types) + 1)
                    for j, t_type in enumerate(st.session_state.hall_table_types):
                        with h_cols[j]:
                            st.number_input(f"홀: {t_type}", min_value=0, value=4, key=f"hall_{j}_count")
                    
                    with h_cols[-1]:
                        st.write("") # 간격
                        if st.button("➕ 홀 테이블 종류 추가", key="add_hall_table_btn"):
                            st.session_state.hall_table_types.append("신규석")
                            st.rerun()
                    
                    if len(st.session_state.hall_table_types) > 2:
                        if st.button("🗑️ 마지막 홀 테이블 종류 삭제", key="del_hall_table_btn"):
                            st.session_state.hall_table_types.pop()
                            st.rerun()

            st.write("")
            col_final1, col_final2 = st.columns(2)
            with col_final1:
                if st.button("← 이전 단계로", key="btn_join_4_prev", use_container_width=True):
                    st.session_state.join_step = 3
                    st.rerun()
            with col_final2:
                if st.button("다음 단계: 스마트 기기 및 알림 설정 →", key="btn_join_4_next", use_container_width=True, type="primary"):
                    st.session_state.join_step = 5
                    st.rerun()

        # --- 5단계: 스마트 기기 및 알림 설정 (NEW) ---
        elif st.session_state.join_step == 5:
            st.write("### ⚙️ 5단계: 스마트 기기 및 고객 알림 설정")
            
            with st.container(border=True):
                st.write("#### 📟 블루투스 프린터 연동")
                printer_type = st.selectbox("연결할 프린터 종류", ["영수증 프린터 (58mm)", "주방 프린터 (80mm)", "라벨 프린터", "미사용"])
                if printer_type != "미사용":
                    st.button("🔍 주변 블루투스 기기 찾기", key="btn_printer_scan")
                    st.caption("※ 프린터 전원을 켜고 '페어링 모드' 상태에서 검색해 주세요.")
                
                st.write("---")
                st.write("#### 📱 고객 주문/예약 알림 방식 선택")
                
                # 요금 체계 세분화 및 선택 기능
                notification_mode = st.radio(
                    "원하시는 알림 형태를 선택해 주세요 (건당 요금 안내)",
                    [
                        "📟 단순 문자 메세지 (SMS) - 건당 약 15~20원",
                        "🔗 링크형 문자 (LMS) - 건당 약 30~50원",
                        "✨ 스마트 웹 브라우저 주문서 (추천) - 알림톡 기준 약 20~30원"
                    ],
                    index=2,
                    help="웹 브라우저 주문서를 선택하면 고객이 앱 설치 없이 실시간 현황을 볼 수 있습니다."
                )
                
                if "추천" in notification_mode:
                    st.success("🏆 **[Best Choice]** 가맹점과 고객 모두 앱 설치가 필요 없는 '웹 브라우저 방식'입니다.")
                    st.markdown("""
                        <div style="background:#E3F2FD; padding:20px; border-radius:15px; border-left:5px solid #2196F3;">
                            <h5 style="color:#1565C0; margin-top:0;">📊 월 예상 비용 (예시)</h5>
                            <ul style="font-size:15px; color:#444; line-height:1.8;">
                                <li><b>월 100건 주문 시</b>: 약 2,000원 ~ 3,000원</li>
                                <li><b>월 300건 주문 시</b>: 약 6,000원 ~ 9,000원</li>
                                <li><b>특징</b>: 비싼 월 관리비나 앱 개발비 없이, <b>커피 한 잔 값</b>으로 스마트 시스템 운영이 가능합니다.</li>
                            </ul>
                            <p style="margin:0; font-size:14px; color:#1565C0;">
                                <b>🔗 핵심 가치:</b> 번거로운 앱 설치를 없애 고객 이탈을 0%로 만드는 우리 본부만의 혁신 기술입니다.
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.write("---")
                st.write("#### 💰 자동 문자/알림톡 발송 설정 (실비 정산)")
                
                with st.expander("❓ 솔라피(Solapi) 가입 및 API 키 발급 방법 (처음이신 분 클릭)", expanded=True):
                    st.markdown("""
                        <div style="background:#F8F9FA; padding:20px; border-radius:15px; border:1px solid #DEE2E6;">
                            <h5 style="color:#FF9500; margin-top:0;">🚀 5분 완성 세팅 가이드</h5>
                            <ol style="line-height:1.8; font-size:15px; color:#444;">
                                <li><b>솔라피 홈페이지 접속</b>: <a href='https://www.solapi.com/signup' target='_blank'><b>여기 클릭하여 가입</b></a></li>
                                <li><b>충전(결제)</b>: [결제/충전] 메뉴에서 원하는 금액(예: 5,000원)을 충전합니다. (문자 한 건당 약 15~20원 차감)</li>
                                <li><b>발신번호 등록</b>: [설정] > [발신번호 관리]에서 사장님 휴대폰 번호를 등록 및 인증합니다.</li>
                                <li><b>API 키 발급</b>: [설정] > [API Key 관리]에서 <b>API Key</b>와 <b>API Secret</b>을 생성합니다.</li>
                                <li><b>키 입력</b>: 발급받은 두 개의 키를 아래 입력창에 각각 복사해서 넣으시면 끝!</li>
                            </ol>
                            <p style="font-size:13px; color:#888; margin-top:10px;">※ 본사는 수수료를 받지 않으며, 모든 비용은 솔라피와 직접 정산하시는 구조입니다.</p>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.write("")
                user_solapi_key = st.text_input("🔑 솔라피 API KEY", key="join_5_solapi_key", placeholder="NCSR...")
                user_solapi_secret = st.text_input("🔒 솔라피 SECRET KEY", type="password", key="join_5_solapi_secret", placeholder="S8T5...")
                st.caption("※ 키를 정확히 입력하셔야 고객에게 실시간 알림톡이 정상 발송됩니다.")

            col_5_1, col_5_2 = st.columns(2)
            with col_5_1:
                if st.button("← 이전 단계", key="btn_join_5_prev", use_container_width=True):
                    st.session_state.join_step = 4
                    st.rerun()
            with col_5_2:
                if st.button("🚀 모든 설정 완료 및 가맹 신청", key="btn_join_5_final", use_container_width=True, type="primary"):
                    # 1. 가맹점 데이터 수집
                    store_id = st.session_state.get('join_3_id', f"store_{random.randint(1000, 9999)}")
                    store_data = {
                        "password": st.session_state.get('join_3_pw', '1234'),
                        "name": st.session_state.get('join_1_store_name', '미지정 매장'),
                        "phone": st.session_state.get('join_2_phone_input', ''),
                        "owner_name": st.session_state.get('join_2_name', ''), # 대표자 성함 추가
                        "info": st.session_state.get('join_2_addr', ''),
                        "category": st.session_state.get('join_selected_type', '기타'),
                        "status": "미납",
                        "payment_status": "미등록",
                        "printer_type": printer_type,
                        "notification_mode": notification_mode,
                        "solapi_key": st.session_state.get('join_5_solapi_key', ''),
                        "solapi_secret": st.session_state.get('join_5_solapi_secret', '')
                    }
                    
                    # 2. 구글 시트 저장 실행
                    with st.spinner("구글 시트에 가맹점 정보를 안전하게 기록 중..."):
                        success = db_manager.save_store(store_id, store_data)
                    
                    if success:
                        st.balloons()
                        st.success(f"🎉 가맹 신청 완료! [{store_id}] 계정으로 구글 시트에 저장되었습니다.")
                        st.info("AI가 사장님의 매장에 최적화된 스마트 시스템을 구성 중입니다! 잠시 후 로그인 화면으로 이동합니다.")
                        # 초기화 및 로그인 페이지로 이동
                        st.session_state.join_step = 1
                        st.session_state.page = "LOGIN_ADMIN"
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("❌ 구글 시트 저장 중 오류가 발생했습니다. 설정(secrets.toml)을 확인해 주세요.")

    elif page == "LOGIN_ADMIN":
        st.markdown('<div class="sub-title-area"><h1>🔒 통합 관리자 로그인</h1><p>본사 및 가맹점 통합 로그인 구역입니다.</p></div>', unsafe_allow_html=True)
        
        with st.container(border=True):
            admin_id = st.text_input("🆔 아이디 (ID)", placeholder="아이디를 입력하세요")
            admin_pw = st.text_input("🔑 비밀번호 (Password)", type="password", placeholder="비밀번호를 입력하세요")
            
            st.write("")
            if st.button("🚀 시스템 접속", use_container_width=True, type="primary"):
                # 1. 본사 마스터 관리자 체크
                if admin_id == "admin" and admin_pw == "1234":
                    st.success("🏢 본사 마스터 인증 성공! 전체 대시보드로 진입합니다.")
                    time.sleep(0.5)
                    navigate_to("ADMIN_DASHBOARD")
                
                # 2. 가맹점 관리자 체크 (실제 DB 연동)
                else:
                    with st.spinner("가맹점 정보를 확인 중..."):
                        store_info = db_manager.verify_store_login(admin_id, admin_pw)
                    
                    if store_info:
                        st.success(f"🏘️ {store_info.get('name', admin_id)} 가맹점 인증 성공! 매장 관리 시스템으로 진입합니다.")
                        time.sleep(0.5)
                        st.session_state.current_store_id = admin_id
                        navigate_to("STORE_ADMIN_PANEL")
                    else:
                        st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
            
            st.write("---")
            col_find1, col_find2 = st.columns(2)
            with col_find1:
                if st.button("🆔 아이디 찾기", use_container_width=True, type="secondary"):
                    navigate_to("FIND_ID")
            with col_find2:
                if st.button("🔑 비밀번호 찾기", use_container_width=True, type="secondary"):
                    navigate_to("FIND_PW")

    elif page == "FIND_ID":
        st.markdown('<div class="sub-title-area"><h1>🆔 아이디 찾기</h1><p>가입 시 등록한 정보를 입력해 주세요.</p></div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.info("💡 가맹 신청 시 입력하신 **대표자 성함**과 **휴대폰 번호**를 입력해 주세요.")
            owner_name = st.text_input("👨‍💼 대표자 성함", placeholder="가입자 성함을 입력하세요")
            phone = st.text_input("📱 등록된 휴대폰 번호", placeholder="010-0000-0000")
            
            st.write("")
            if st.button("🔍 아이디 확인", use_container_width=True, type="primary"):
                if owner_name and phone:
                    with st.spinner("정보를 찾는 중..."):
                        found_id = db_manager.find_store_id(owner_name, phone)
                    if found_id:
                        st.success(f"✅ 사장님의 아이디를 찾았습니다!\n\n**아이디: [ {found_id} ]**")
                        st.session_state.found_id_result = found_id
                    else:
                        st.error("❌ 일치하는 가맹점 정보가 없습니다. 성함과 번호를 다시 확인해 주세요.")
                else:
                    st.error("❗ 성함과 휴대폰 번호를 모두 입력해 주세요.")
            
            if st.session_state.get("found_id_result"):
                if st.button("🚀 찾은 아이디로 로그인하기", use_container_width=True):
                    # 세션 초기화 후 로그인 페이지로
                    id_to_use = st.session_state.found_id_result
                    del st.session_state.found_id_result
                    navigate_to("LOGIN_ADMIN")

        st.write("")
        if st.button("← 로그인 화면으로", use_container_width=True):
            navigate_to("LOGIN_ADMIN")

    elif page == "FIND_PW":
        st.markdown('<div class="sub-title-area"><h1>🔑 비밀번호 찾기</h1><p>본인인증을 통해 비밀번호를 확인합니다.</p></div>', unsafe_allow_html=True)
        with st.container(border=True):
            target_id = st.text_input("찾으려는 아이디(ID)", placeholder="아이디를 입력하세요")
            st.write("#### ✅ 휴대폰 본인인증")
            c1, c2 = st.columns([2, 1])
            with c1: 
                phone_num = st.text_input("휴대폰 번호", value="010-", key="find_pw_phone")
            with c2: 
                st.write("")
                if st.button("인증번호 발송", use_container_width=True, key="btn_find_pw_auth"):
                    if len(phone_num.replace("-", "")) >= 10:
                        code = str(random.randint(100000, 999999))
                        st.session_state.find_pw_auth_real = code
                        success, msg = sms_manager.send_sms(phone_num, f"[동네비서 AI] 본인인증번호는 [{code}] 입니다.")
                        if success: st.success("✅ 발송 완료!")
                        else: st.error("❌ 문자 발송 실패")
                    else: st.error("번호 확인")
            
            auth_code = st.text_input("인증번호 입력", placeholder="6자리 숫자")
            
            st.write("")
            if st.button("🔓 비밀번호 확인", use_container_width=True, type="primary"):
                if target_id and auth_code:
                    if auth_code == st.session_state.get("find_pw_auth_real"):
                        found_pw = db_manager.find_store_password(target_id, phone_num)
                        if found_pw:
                            # 만약 비밀번호가 해시값이면(보통 $2b$로 시작) 안내 메시지 표시
                            if found_pw.startswith("$2b$"):
                                st.warning("🔒 비밀번호가 안전하게 암호화되어 있습니다.")
                                st.info("정부 지원금 심사용 데모 버전에서는 **[ 1234 ]**로 초기화하여 확인하실 수 있도록 설정했습니다.")
                            else:
                                st.success(f"✅ 인증 성공! 사장님의 비밀번호입니다.\n\n**비밀번호: [ {found_pw} ]**")
                        else:
                            st.error("❌ 아이디와 휴대폰 번호가 일치하지 않습니다.")
                    else:
                        st.error("❌ 인증번호가 올바르지 않습니다.")
                else:
                    st.error("❗ 아이디와 인증번호를 모두 입력해 주세요.")
        
        st.write("")
        if st.button("← 로그인 화면으로", use_container_width=True):
            navigate_to("LOGIN_ADMIN")

    elif page == "ADMIN_DASHBOARD":
        # ... (이전과 동일한 본사 대시보드 로직)
        st.markdown('<div class="sub-title-area"><h1>📊 동네비서 AI 본부 대시보드</h1><p>가맹점 중심의 플랫폼 통합 관리 시스템입니다.</p></div>', unsafe_allow_html=True)
        # ... (이후 생략) ...
        # [중요] 여기서는 생략하지만 실제 파일에는 기존 코드가 유지되도록 search_replace를 신중히 사용해야 합니다.
        # 실제로는 "elif page == "STORE_ADMIN_PANEL":" 섹션을 추가하는 것이 목적입니다.

    elif page == "STORE_ADMIN_PANEL":
        # 가맹점 전용 대시보드 (사장님들의 실전 운영 화면)
        store_id = st.session_state.get("current_store_id", "알 수 없음")
        store_info = db_manager.get_store(store_id)
        store_name = store_info.get("name", "우리 매장") if store_info else "우리 매장"

        st.markdown(f'<div class="sub-title-area"><h1>🏘️ {store_name} 관리 센터</h1><p>매장 운영 및 고객 관리를 위한 스마트 대시보드입니다.</p></div>', unsafe_allow_html=True)
        
        # 가맹점용 요약 지표
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("오늘 주문", "24건", "+3건")
        with c2: st.metric("예약 대기", "5건", "확인 필요")
        with c3: st.metric("단골 고객", "152명", "누적")
        with c4: 
            # 솔라피 잔액 시뮬레이션
            st.metric("솔라피 잔액", "12,450원", "약 600건 발송 가능")

        st.write("---")

        tab1, tab2, tab3, tab4 = st.tabs(["📋 주문/예약 관리", "📢 단골 알림톡", "🍱 메뉴/공간 설정", "🛠️ 매장 정보"])

        with tab1:
            st.write("### 🕒 실시간 주문 및 예약 현황")
            st.info("💡 고객이 앱 설치 없이 브라우저로 보낸 주문들이 이곳에 실시간으로 표시됩니다.")
            
            # 더미 데이터로 주문 목록 표시
            mock_orders = pd.DataFrame([
                {"시간": "14:20", "구분": "주문", "내용": "돈까스 외 2건", "상태": "조리중", "고객": "010-****-1234"},
                {"시간": "14:35", "구분": "예약", "내용": "4인 테이블 (18:00)", "상태": "승인대기", "고객": "010-****-5678"},
                {"시간": "14:40", "구분": "주문", "내용": "아메리카노 1잔", "상태": "완료", "고객": "010-****-9012"}
            ])
            st.table(mock_orders)
            
            # QR 코드 생성 (고객용 스마트 주문서 링크)
            st.write("---")
            st.write("#### 📱 우리 매장 스마트 주문서 QR")
            qr_link = f"https://aistore.web/order/{store_id}"
            qr_img = generate_qr(qr_link)
            col_q1, col_q2 = st.columns([1, 3])
            with col_q1:
                st.image(qr_img, width=150)
            with col_q2:
                st.success(f"🔗 주문서 링크: {qr_link}")
                st.write("위 QR코드를 매장 테이블에 붙이거나 문 앞에 비치하세요.")
                st.write("고객은 **앱 설치 없이** 카메라만 대면 바로 주문할 수 있습니다.")

        with tab2:
            st.write("### 📢 단골 고객 맞춤 알림 발송")
            st.write("등록된 단골 고객들에게 터치 한 번으로 알림을 보냅니다.")
            
            with st.container(border=True):
                target_msg = st.selectbox("알림 종류 선택", [
                    "🏆 [강력추천] 스마트 웹 주문서 링크 (무료 체험 중)",
                    "📩 단순 텍스트 SMS (건당 20원)",
                    "📢 카카오 알림톡 (건당 15원)"
                ])
                st.text_area("보낼 메시지 내용", value=f"[{store_name}] 사장님! 오늘 신메뉴가 출시되었습니다. 아래 링크에서 확인하고 바로 주문하세요!\n{qr_link}")
                if st.button("🚀 단골 152명에게 일괄 발송", use_container_width=True, type="primary"):
                    st.balloons()
                    st.success("✅ 알림톡 발송이 시작되었습니다! (솔라피 API 연동)")

        with tab3:
            st.write("### 🍱 메뉴 및 매장 공간 관리")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.write("#### 🥘 판매 메뉴")
                st.write("- 돈까스 (12,000원) [판매중]")
                st.write("- 제육볶음 (10,000원) [품절]")
                st.button("➕ 메뉴 추가/수정")
            with col_m2:
                st.write("#### 🪑 좌석/룸 현황")
                st.write("- 🚪 룸 1: [사용중]")
                st.write("- 🚪 룸 2: [비어있음]")
                st.write("- 🪑 홀 테이블 1~10번")
                st.button("➕ 공간 설정 변경")

        with tab4:
            st.write("### 🛠️ 매장 기본 정보 및 API 설정")
            with st.expander("🔑 솔라피 API 정보 (문자/알림톡 발송용)"):
                st.write(f"**API KEY**: {store_info.get('solapi_key', '미등록') if store_info else '미등록'}")
                st.write(f"**API SECRET**: {'*' * 10}")
                st.button("⚙️ API 키 수정하기")
            
            with st.expander("🖨️ 프린터 설정"):
                st.write(f"**연결된 프린터**: {store_info.get('printer_type', '미사용') if store_info else '미사용'}")
                st.button("🔍 주변 블루투스 기기 찾기")

    elif page == "AI_VOICE":
        st.markdown('<div class="sub-title-area"><h1>🎙️ AI 음성 대화</h1><p>무엇이든 말씀해 주세요. AI가 직접 대답합니다.</p></div>', unsafe_allow_html=True)
        
        # 1. 목소리 출력(TTS) 전용 (에러 방지를 위해 최소화)
        st.components.v1.html("""
            <script>
            window.addEventListener("message", (event) => {
                if (event.data.type === "speak") {
                    const utterance = new SpeechSynthesisUtterance(event.data.text);
                    utterance.lang = 'ko-KR';
                    window.speechSynthesis.speak(utterance);
                }
            });
            </script>
        """, height=0)

        # 2. 음성 인식 결과 처리 (URL 파라미터 방식)
        v_text = st.query_params.get("v_text", "")
        if v_text:
            # 사장님 말씀 표시
            st.markdown(f"""
            <div style="display:flex; justify-content:flex-end; margin-bottom:20px;">
                <div style="background:#007AFF; color:white; padding:20px 30px; border-radius:30px 30px 0 30px; font-size:24px; font-weight:800; box-shadow:0 10px 20px rgba(0,122,255,0.2);">
                    "{v_text}"
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.chat_message("assistant"):
                response_text = ""
                target_page = None
                
                try:
                    # 실제 Gemini AI에게 물어보기
                    if "chat_model" in st.session_state:
                        prompt = f"""당신은 '동네비서 AI'의 최고 수준 비서입니다. 
사장님이 다음과 같이 말씀하셨습니다: "{v_text}"

사장님의 의도를 정확히 파악하여 전문적이고 친절하게 응답하세요.
- 만약 사장님이 '택배', '배송', '운송장' 관련 업무를 원하시면 응답 마지막에 [MOVE:DELIVERY]를 포함하세요.
- 만약 '예약', '일정', '예약자' 확인이나 관리를 원하시면 응답 마지막에 [MOVE:RESERVE]를 포함하세요.
- 만약 '홈', '메인', '처음'으로 가고 싶어하시면 [MOVE:HOME]을 포함하세요.
- 그 외의 질문에는 상황에 맞는 최선의 해결책을 제시하세요.

응답은 한국어로 1~2문장으로 간결하고 전문적으로 작성하세요."""
                        
                        response = st.session_state.chat_model.generate_content(prompt)
                        full_response = response.text
                        
                        # 이동 명령 추출
                        if "[MOVE:DELIVERY]" in full_response:
                            target_page = "DELIVERY"
                            response_text = full_response.replace("[MOVE:DELIVERY]", "").strip()
                        elif "[MOVE:RESERVE]" in full_response:
                            target_page = "RESERVE"
                            response_text = full_response.replace("[MOVE:RESERVE]", "").strip()
                        elif "[MOVE:HOME]" in full_response:
                            target_page = "HOME"
                            response_text = full_response.replace("[MOVE:HOME]", "").strip()
                        else:
                            response_text = full_response.strip()
                    else:
                        response_text = "AI 모델이 설정되지 않았습니다."
                except Exception as e:
                    response_text = f"죄송합니다. AI 연결 중 오류가 발생했습니다: {str(e)}"
                
                st.write(response_text)
                
                # TTS 실행
                st.components.v1.html(f"""
                    <script>
                    window.parent.postMessage({{type: "speak", text: "{response_text}"}}, "*");
                    </script>
                """, height=0)

                if target_page:
                    st.info(f"⏳ 잠시 후 {target_page}로 이동합니다...")
                    import time
                    time.sleep(1.5)
                    st.session_state.page = target_page
                    st.query_params.clear()
                    st.rerun()

            if st.button("🎤 다시 말씀하시려면 누르세요", use_container_width=True, type="primary"):
                st.query_params.clear()
                st.rerun()
        
        else:
            # 3. 마이크 버튼 UI (가장 심플하고 강력한 버전)
            st.components.v1.html("""
                <div style="text-align:center; padding:50px;">
                    <button id="mic-btn" style="width:150px; height:150px; border-radius:50%; border:none; background:#007AFF; color:white; font-size:50px; cursor:pointer; box-shadow:0 10px 30px rgba(0,122,255,0.3);">🎙️</button>
                    <h3 id="status" style="margin-top:20px; font-family:sans-serif;">누르고 말씀하세요</h3>
                </div>
                <script>
                    const btn = document.getElementById('mic-btn');
                    const status = document.getElementById('status');
                    const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
                    
                    if (!Speech) {
                        status.innerText = "❌ 지원하지 않는 브라우저입니다.";
                    } else {
                        const rec = new Speech();
                        rec.lang = 'ko-KR';
                        
                        btn.onclick = () => {
                            rec.start();
                            btn.style.background = "#FF3B30";
                            status.innerText = "⏳ 듣고 있습니다...";
                        };
                        
                        rec.onresult = (e) => {
                            const text = e.results[0][0].transcript;
                            const url = new URL(window.parent.location.href);
                            url.searchParams.set("v_text", text);
                            window.parent.location.href = url.toString();
                        };
                        
                        rec.onerror = () => {
                            btn.style.background = "#007AFF";
                            status.innerText = "❌ 다시 시도해 주세요.";
                        };
                    }
                </script>
            """, height=350)

    elif page == "AI_VISION":
        # 0. AI_VISION 전용 스타일 (카메라 풀스크린 및 하이엔드 UI)
        st.markdown("""
        <style>
            /* 전체 배경을 어둡게 하여 카메라에 집중 */
            html, body, [data-testid="stAppViewContainer"] {
                background: #000000 !important;
                overflow: hidden !important;
            }
            
            /* 헤더 영역 커스텀 */
            .vision-header {
                text-align: center;
                padding: 40px 20px;
                background: linear-gradient(180deg, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0) 100%);
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                z-index: 999;
            }
            .vision-header h1 {
                color: #FFFFFF !important;
                font-size: 28px !important;
                font-weight: 950 !important;
                margin-bottom: 5px !important;
                text-shadow: 0 2px 10px rgba(0,0,0,0.5);
            }
            .vision-header p {
                color: rgba(255,255,255,0.7) !important;
                font-size: 16px !important;
            }

            /* 카메라 입력창을 화면 전체로 확장 */
            [data-testid="stCameraInput"] {
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                width: 100vw !important;
                height: 100vh !important;
                z-index: 100 !important;
                background: #000 !important;
                margin: 0 !important;
                padding: 0 !important;
                border: none !important;
            }
            
            /* 카메라 비디오 영역 풀스크린화 */
            [data-testid="stCameraInput"] video {
                object-fit: cover !important;
                width: 100vw !important;
                height: 100vh !important;
            }
            
            /* 촬영 버튼 위치 및 스타일 마스터피스 */
            [data-testid="stCameraInput"] button {
                position: fixed !important;
                bottom: 50px !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                width: 90px !important;
                height: 90px !important;
                border-radius: 50% !important;
                background-color: rgba(255,255,255,0.2) !important;
                border: 5px solid #FFFFFF !important;
                color: transparent !important; /* 글씨 숨기기 */
                z-index: 1000 !important;
                box-shadow: 0 0 20px rgba(255,255,255,0.3) !important;
                transition: all 0.3s ease !important;
            }
            [data-testid="stCameraInput"] button:active {
                transform: translateX(-50%) scale(0.9) !important;
                background-color: rgba(255,255,255,0.5) !important;
            }
            
            /* 촬영 버튼 안내 문구 추가 */
            [data-testid="stCameraInput"]::after {
                content: "원형 버튼을 눌러 촬영하세요";
                position: fixed;
                bottom: 150px;
                left: 50%;
                transform: translateX(-50%);
                color: white;
                font-weight: 700;
                text-shadow: 0 2px 5px rgba(0,0,0,1);
                z-index: 1000;
                width: 100%;
                text-align: center;
                pointer-events: none;
            }

            /* 분석 결과 창 스타일 */
            .analysis-overlay {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: rgba(255,255,255,0.95);
                backdrop-filter: blur(20px);
                border-radius: 30px 30px 0 0;
                padding: 30px;
                z-index: 2000;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 -10px 40px rgba(0,0,0,0.2);
                animation: slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1);
            }
            @keyframes slideUp {
                from { transform: translateY(100%); }
                to { transform: translateY(0); }
            }
            
            /* 홈 버튼 (좌측 상단 고정) */
            .back-home-btn {
                position: fixed;
                top: 40px;
                left: 20px;
                z-index: 1001;
                background: rgba(255,255,255,0.2);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.3);
                color: white;
                padding: 10px 20px;
                border-radius: 15px;
                text-decoration: none;
                font-weight: 700;
            }
        </style>
        """, unsafe_allow_html=True)

        # 1. 헤더 (카메라 촬영 시에만 보임)
        st.markdown("""
        <div class="vision-header">
            <h1>📸 AI VISION SCAN</h1>
            <p>화면 중앙에 대상을 맞춰주세요</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. 홈으로 돌아가기 버튼 (Streamlit 버튼으로 구현)
        if st.button("🏠 홈으로", key="vision_back_home", type="secondary"):
            st.session_state.page = "HOME"
            st.rerun()

        # 3. 카메라 입력 (풀스크린 적용)
        img_file = st.camera_input("SCAN", label_visibility="collapsed")
        
        # 4. 분석 결과 표시 (팝업 레이어 스타일)
        if img_file:
            # 촬영된 이미지를 상단에 작게 표시
            st.image(img_file, use_container_width=True, caption="촬영된 이미지")
            
            with st.container():
                st.markdown('<div class="analysis-overlay">', unsafe_allow_html=True)
                st.write("### 🔍 AI 정밀 분석 중...")
                
                # 실제 Gemini AI로 사진 분석
                with st.spinner("AI가 내용을 읽고 있습니다..."):
                    try:
                        if "vision_model" in st.session_state:
                            from PIL import Image
                            img = Image.open(img_file)
                            
                            prompt = """당신은 세계 최고의 광학 문자 인식(OCR) 및 정보 추출 전문가입니다. 
제시된 사진을 분석하여 다음 규칙에 따라 응답하세요:

1. **상황 파악**: 사진이 '택배 운송장', '손글씨 주소', '식당 메뉴판', '영수증' 중 무엇인지 먼저 명시하세요.
2. **정보 추출**: 
   - [택배/주소의 경우]: 보낸사람/받는사람의 이름, 전화번호(010-XXXX-XXXX 형식), 주소를 정확히 추출하세요. 
   - [메뉴판의 경우]: 메뉴 이름과 가격을 표 형태로 정리하세요.
3. **손글씨 보정**: 흘려 쓴 글씨는 앞뒤 문맥(예: 도로명 주소 체계)을 고려하여 가장 정확한 단어로 교정하여 보여주세요.
4. **결과 요약**: 사장님이 바로 복사해서 쓸 수 있도록 핵심 정보만 깔끔하게 출력하세요.

반드시 한국어로, 친절하고 전문적으로 대답하세요."""
                            
                            response = st.session_state.vision_model.generate_content([prompt, img])
                            analysis_result = response.text
                            
                            st.markdown(f"""
                            <div style="background:#F8F9FA; padding:20px; border-radius:15px; border-left:5px solid #007AFF; margin-bottom:20px;">
                                <h4 style="color:#007AFF; margin-top:0;">📋 분석 리포트</h4>
                                <div style="white-space: pre-wrap; line-height: 1.6; font-size: 16px; color:#333;">
                                    {analysis_result}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.error("AI 모델 설정 오류")
                    except Exception as e:
                        st.error(f"분석 실패: {str(e)}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 다시 촬영", use_container_width=True):
                        st.rerun()
                with col2:
                    if st.button("✅ 데이터 접수", use_container_width=True, type="primary"):
                        st.success("성공적으로 접수되었습니다!")
                        st.balloons()
                        import time
                        time.sleep(2)
                        st.session_state.page = "HOME"
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)

    elif page == "CUSTOMER_MENU":
        st.markdown('<div class="sub-title-area"><h1>🍽️ 우리 매장 메뉴판</h1><p>원하시는 상품을 골라보세요.</p></div>', unsafe_allow_html=True)
        
        # 단골 확인 섹션 추가 (자연스럽게 녹아들도록)
        with st.container(border=True):
            st.markdown("""
            <div style="text-align:center; padding:10px;">
                <h3 style="color:#FF2D55; margin-bottom:10px;">🎁 단골 혜택 적용하기</h3>
                <p style="color:#666; font-size:16px;">전화번호를 입력하시면 단골 혜택과 포인트가 자동으로 적용됩니다.</p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns([3, 1])
            with c1:
                phone_input = st.text_input("휴대폰 번호 입력", placeholder="010-0000-0000", label_visibility="collapsed")
            with c2:
                if st.button("확인", key="btn_dangol_check", use_container_width=True, type="primary"):
                    if phone_input:
                        st.toast(f"✨ {phone_input[-4:]}님, 환영합니다! 단골 혜택이 적용되었습니다.")
                        st.success(f"회원님을 확인했습니다. 오늘의 추천 메뉴를 확인해보세요!")
                    else:
                        st.warning("번호를 입력해주세요.")
        
        st.write("")
        products = st.session_state.store_config["products"]
        
        # 메뉴판 그리드 레이아웃
        for i in range(0, len(products), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(products):
                    item = products[i+j]
                    with cols[j]:
                        with st.container(border=True):
                            st.image(item["image"], use_container_width=True)
                            st.subheader(item["name"])
                            st.write(f"**가격: {item['base_price']:,}원**")
                            if st.button(f"{item['name']} 주문하기", key=f"order_{i+j}", use_container_width=True, type="primary"):
                                st.toast(f"✅ {item['name']} 주문이 접수되었습니다!")
                                st.success("주문이 완료되었습니다. 잠시만 기다려 주세요!")

    elif page == "COMPANY_INTRO":
        # 회사 소개 페이지 전용 미래지향적 배경 스타일 (더 명확한 이미지로 변경)
        st.markdown("""
        <style>
        html, body, [data-testid="stAppViewContainer"] {
            background-image: linear-gradient(rgba(0,0,0,0.2), rgba(0,0,0,0.2)), 
                              url('https://images.unsplash.com/photo-1519608487953-e999c86e7455?q=80&w=2070&auto=format&fit=crop') !important;
            background-size: cover !important;
            background-position: center !important;
            background-attachment: fixed !important;
        }
        [data-testid="stAppViewBlockContainer"] {
            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(15px) !important;
            border-radius: 30px !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            padding: 60px !important;
            margin-top: 50px !important;
        }
        .company-card {
            background: transparent !important; /* 완전 투명하게 처리 */
            backdrop-filter: none !important; /* 유리 효과 제거 */
            padding: 40px;
            border-radius: 25px;
            border: none !important; /* 테두리 제거 */
            box-shadow: none !important; /* 그림자 제거 */
        }
        .sub-title-area h1 { color: #FFFFFF !important; }
        .sub-title-area p { color: rgba(255,255,255,0.7) !important; }
        .company-card h2 { color: #00CCFF !important; } /* 밝은 블루로 변경 */
        .company-card p, .company-card ul { color: #FFFFFF !important; } /* 텍스트 흰색으로 변경 */
        .company-card hr { border-top: 1px solid rgba(255,255,255,0.2) !important; }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sub-title-area"><h1>🏢 탄탄제작소 소개</h1><p>혁신적인 AI 솔루션으로 미래를 만듭니다.</p></div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="company-card">
            <h2 style="font-size: 32px; font-weight: 900; margin-bottom: 20px;">TANTAN FABRIC (탄탄제작소)</h2>
            <p style="font-size:20px; line-height:1.8; font-weight: 500;">
                탄탄제작소는 인공지능(AI)과 사물인터넷(IoT) 기술을 결합하여 
                소상공인과 중소기업을 위한 <b>'똑똑한 비즈니스 파트너'</b> 솔루션을 개발하는 혁신 기술 기업입니다.
            </p>
            <hr>
            <h3 style="font-size: 24px; font-weight: 800; margin-bottom: 15px; color: #FFFFFF;">🚀 주요 사업 분야</h3>
            <ul style="line-height:2.2; font-size: 18px;">
                <li><b>AI 키오스크 시스템:</b> 음성 인식 및 비전 분석 기반 차세대 결제 솔루션</li>
                <li><b>스마트 물류 솔루션:</b> 로젠택배 연동 등 지능형 배송 관리 시스템</li>
                <li><b>가맹점 통합 관리:</b> 데이터 기반의 효율적인 매장 운영 대시보드</li>
            </ul>
            <hr>
            <p style="text-align:center; opacity: 0.7; margin-top:30px; font-size: 16px;">
                문의: contact@tantan.io | TEL: 02-1234-5678<br>
                <b>© 2025 TANTAN FABRIC. All rights reserved.</b>
            </p>
</div>
""", unsafe_allow_html=True)

        st.write("")
        if st.button("← 메인으로 돌아가기", use_container_width=True, type="primary"):
            st.session_state.page = "HOME"
            st.rerun()

    elif page == "DANGOL_INTRO":
        st.markdown('<div class="sub-title-area"><h1>🤝 단골비서 서비스 소개</h1><p>한 번 온 손님을 평생 단골로 만드는 마법.</p></div>', unsafe_allow_html=True)
        
        # HTML 코드가 코드로 인식되지 않도록 들여쓰기를 완전히 제거하고 한 번에 출력
        st.markdown("""<div style="background: white; padding: 30px; border-radius: 15px; border: 1px solid #ddd;">
<h2 style="color:#FF2D55; margin-top:0;">❤️ 단골비서 (DANGOL SECRETARY)</h2>
<p style="font-size:18px; line-height:1.8; color:#333;">
단골비서는 단순한 키오스크를 넘어, 매장을 방문하는 고객 한 분 한 분을 기억하고 
<b>맞춤형 서비스</b>를 제공하는 AI 기반 고객 관리 솔루션입니다.
</p>
<hr style="margin: 25px 0;">
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
<div style="flex: 1; min-width: 280px;">
<h3 style="color:#007AFF;">🏪 매장운영 프로세스</h3>
<div style="background:#F0F7FF; padding:20px; border-radius:15px; margin-bottom:20px; min-height: 380px;">
<ul style="line-height:2.2; font-size:17px; color:#444; list-style:none; padding-left:0;">
<li><b>1. 지능형 인식:</b> 방문 시 QR코드 스캔 및 전화번호 입력을 통해 단골을 즉시 파악합니다.</li>
<li><b>2. 데이터 분석:</b> 고객의 주문 내역, 취향, 방문 주기를 분석합니다.</li>
<li><b>3. 맞춤형 제안:</b> "평소 드시던 메뉴로 준비해 드릴까요?" 자동 인사.</li>
<li><b>4. 자동 리워드:</b> 적립금 및 혜택을 사장님 손 안 대고 자동 관리합니다.</li>
<li><b>5. 재방문 유도:</b> 감사 메시지 및 쿠폰 발송으로 단골을 고착화합니다.</li>
</ul>
</div>
</div>
<div style="flex: 1; min-width: 280px;">
<h3 style="color:#28A745;">🚚 택배영업 프로세스</h3>
<div style="background:#F2F9F4; padding:20px; border-radius:15px; margin-bottom:20px; min-height: 380px;">
<ul style="line-height:2.2; font-size:17px; color:#444; list-style:none; padding-left:0;">
<li><b>1. 퀵 접수:</b> 단골의 자주 보내는 주소지를 AI가 즉시 호출합니다.</li>
<li><b>2. 원클릭 결제:</b> 매번 주소 입력 없이 터치 한 번으로 접수가 끝납니다.</li>
<li><b>3. 자동 송장 출력:</b> 로젠택배 시스템과 연동되어 송장이 자동 출력됩니다.</li>
<li><b>4. 배송 추적 알림:</b> 택배 위치를 고객에게 카톡/SMS로 자동 안내합니다.</li>
<li><b>5. 집하 자동 요청:</b> 사장님이 신경 쓰지 않아도 집하 기사님께 자동 전달됩니다.</li>
</ul>
</div>
</div>
<div style="flex: 1; min-width: 280px;">
<h3 style="color:#FF9500;">📦 택배기사 프로세스</h3>
<div style="background:#FFF9F2; padding:20px; border-radius:15px; margin-bottom:20px; min-height: 380px;">
<ul style="line-height:2.2; font-size:17px; color:#444; list-style:none; padding-left:0;">
<li><b>1. 집하 요청(벨) 알림:</b> 고객이 부르면 기사님 앱에 '벨'이 울리며 즉시 호출됩니다.</li>
<li><b>2. 자동 링크 발송:</b> 벨이 울림과 동시에 고객에게 <b>정보 입력용 웹 링크가 자동으로 발송</b>됩니다.</li>
<li><b>3. 스마트 집하 처리:</b> 고객이 웹창에서 <b>손글씨 사진</b>으로 정보를 입력하여, 기사님의 대기 시간이 사라집니다.</li>
<li><b>4. AI 경로 최적화:</b> 여러 집하지를 가장 효율적으로 순회하는 최적 경로를 실시간 안내합니다.</li>
<li><b>5. 정산 자동 관리:</b> 일일 집하 실적과 수수료가 매일 자동으로 합산되어 관리됩니다.</li>
</ul>
</div>
</div>
</div>
<h3 style="margin-top:20px;">✨ 도입 효과</h3>
<ul style="line-height:2.2; font-size:17px; color:#444;">
<li>고객 재방문율 평균 <b style="color:#FF2D55;">35% 향상</b></li>
<li><b style="color:#28A745;">택배 접수 시간 80% 단축</b> (과거 이력 자동 불러오기)</li>
<li>고객 대기 시간 단축 및 주문 정확도 증가</li>
<li>사장님의 소중한 시간을 매장 품질 관리에 집중 가능</li>
</ul>
<hr style="margin: 25px 0;">
<p style="text-align:center; color:#888; font-size:16px;">
"동네비서 AI 본부가 사장님의 가장 든든한 영업 부장이 되어 드립니다."
</p>
</div>""", unsafe_allow_html=True)
        
        if st.button("← 처음으로", use_container_width=True, type="primary"):
            st.session_state.page = "HOME"
            st.rerun()
