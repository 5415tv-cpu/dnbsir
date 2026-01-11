import streamlit as st
from datetime import datetime

# 1. 전문가급 키오스크 환경 설정
st.set_page_config(
    page_title="동네비서 KIOSK",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. 고품격 커스텀 CSS (Pretendard 폰트 및 앱 스타일링)
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    /* 글로벌 배경 설정 */
    .stApp {
        background-color: #0F0F12 !important;
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
    }

    /* 상단 영역 여백 제거 */
    .block-container {
        padding: 1.5rem 1rem !important;
        max-width: 550px !important;
        margin: 0 auto !important;
    }

    /* 헤더 디자인 */
    .kiosk-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        padding: 10px 10px 30px 10px;
        color: #FFFFFF;
    }
    .kiosk-header .brand {
        font-size: 28px;
        font-weight: 800;
        letter-spacing: -1px;
    }
    .kiosk-header .brand span {
        color: #4D7CFF; /* 포인트 컬러 */
    }
    .kiosk-header .info {
        text-align: right;
        opacity: 0.8;
    }
    .kiosk-header .time {
        font-size: 30px;
        font-weight: 700;
        line-height: 1;
        margin-bottom: 5px;
    }
    .kiosk-header .date {
        font-size: 14px;
        font-weight: 400;
    }

    /* 그리드 시스템 */
    .kiosk-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 16px;
        padding: 0 5px;
    }

    /* 프리미엄 카드 스타일 */
    .card {
        background: #1E1E24;
        border-radius: 24px;
        padding: 25px 20px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.05);
        min-height: 150px;
        cursor: pointer;
    }

    .card:active {
        transform: scale(0.94);
        background: #25252D;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.5);
    }

    /* 카드 아이콘 및 텍스트 */
    .card-icon {
        font-size: 42px;
        margin-bottom: 12px;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
    }
    .card-title {
        color: #FFFFFF;
        font-size: 18px;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }

    /* 하단 알림 바 */
    .kiosk-footer {
        margin-top: 30px;
        padding: 0 5px;
    }
    .notice-bar {
        background: #FFFFFF;
        border-radius: 100px;
        padding: 12px 20px;
        display: flex;
        align-items: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
    .notice-badge {
        background: #FF3B30;
        color: white;
        font-size: 12px;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 50px;
        margin-right: 15px;
        text-transform: uppercase;
    }
    .notice-text {
        color: #121212;
        font-size: 15px;
        font-weight: 600;
    }

    /* 스트림릿 기본 UI 제거 */
    header, footer, #MainMenu { visibility: hidden !important; }
    [data-testid="stHeader"], [data-testid="stToolbar"] { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 및 화면 구성
now = datetime.now()
time_str = now.strftime('%H:%M')
date_str = now.strftime('%Y. %m. %d') + f" ({['월','화','수','목','금','토','일'][now.weekday()]})"

# 동네비서 10가지 핵심 메뉴
menus = [
    {"title": "매장 예약", "icon": "📅", "color": "#E11E5A"},
    {"title": "택배 접수", "icon": "📦", "color": "#2E7D32"},
    {"title": "고객 관리", "icon": "👥", "color": "#1565C0"},
    {"title": "주문 장부", "icon": "📋", "color": "#EF6C00"},
    {"title": "AI 상담", "icon": "🤖", "color": "#6A1B9A"},
    {"title": "매출 분석", "icon": "📈", "color": "#AD1457"},
    {"title": "문자 발송", "icon": "💬", "color": "#00838F"},
    {"title": "정산 내역", "icon": "💰", "color": "#455A64"},
    {"title": "공지 사항", "icon": "📢", "color": "#F9A825"},
    {"title": "서비스 안내", "icon": "ℹ️", "color": "#37474F"}
]

# 화면 렌더링
st.markdown(f"""
    <div class="kiosk-header">
        <div class="header-left">
            <div class="brand">동네비서<span>.</span></div>
            <div class="weather">소상공인을 위한 스마트 AI 매장관리</div>
        </div>
        <div class="info">
            <div class="time">{time_str}</div>
            <div class="date">{date_str}</div>
        </div>
    </div>
    
    <div class="kiosk-grid">
""", unsafe_allow_html=True)

# 10개 카드 렌더링
for m in menus:
    st.markdown(f"""
        <div class="card">
            <div class="card-icon">{m['icon']}</div>
            <div class="card-title">{m['title']}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown(f"""
    </div>
    <div class="kiosk-footer">
        <div class="notice-bar">
            <span class="notice-badge">Notice</span>
            <span class="notice-text">동네비서 2.0 프리미엄 업데이트가 완료되었습니다.</span>
        </div>
    </div>
""", unsafe_allow_html=True)
