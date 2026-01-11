import streamlit as st
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="동네비서", layout="centered")

# 2. 스타일 및 레이아웃 통합 정의
# (텍스트와 배경색이 무조건 보이도록 !important를 강화했습니다)

now = datetime.now()
time_str = now.strftime('%H : %M')
date_str = now.strftime('%Y. %m. %d') + f" ({['월','화','수','목','금','토','일'][now.weekday()]})"

# 동네비서 전용 10개 메뉴 데이터
menus = [
    {"title": "📅 매장 예약", "color": "#E11E5A"}, # 장미빛
    {"title": "📦 택배 접수", "color": "#2E7D32"}, # 초록
    {"title": "📊 경영 분석", "color": "#1565C0"}, # 파랑
    {"title": "👥 고객 관리", "color": "#EF6C00"}, # 오렌지
    {"title": "💬 문자 발송", "color": "#6A1B9A"}, # 보라
    {"title": "📋 주문 장부", "color": "#455A64"}, # 회색
    {"title": "💰 정산 내역", "color": "#00838F"}, # 청록
    {"title": "📈 매출 통계", "color": "#AD1457"}, # 진분홍
    {"title": "📢 공지 사항", "color": "#F9A825"}, # 황금색
    {"title": "⚙️ 관리자 모드", "color": "#37474F"}  # 청회색
]

# 카드 HTML 생성
cards_html = ""
for m in menus:
    cards_html += f'''
        <div class="menu-item" style="background-color: {m['color']} !important;">
            <div class="menu-text">{m['title']}</div>
        </div>
    '''

st.markdown(f"""
    <style>
    /* 전체 배경: 딥 블랙 */
    .stApp {{
        background-color: #000000 !important;
    }}
    
    /* 상단 헤더 */
    .custom-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 25px 15px 10px 15px;
        color: white;
        max-width: 500px;
        margin: 0 auto;
    }}
    .brand-name {{ font-size: 26px; font-weight: 900; color: #FFFFFF !important; }}
    .weather {{ font-size: 14px; color: #AAAAAA; margin-top: 5px; }}
    .time-section {{ text-align: right; }}
    .current-time {{ font-size: 28px; font-weight: 700; color: #FFFFFF !important; }}
    .current-date {{ font-size: 14px; color: #AAAAAA; }}

    /* 그리드 컨테이너 (2열 고정) */
    .menu-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        padding: 15px;
        max-width: 500px;
        margin: 0 auto;
    }}

    /* 카드 스타일 (터치 전에도 선명하게 보이도록 수정) */
    .menu-item {{
        border-radius: 18px;
        aspect-ratio: 1.3 / 1;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 15px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.5);
        transition: transform 0.1s ease;
        visibility: visible !important;
        opacity: 1 !important;
    }}
    
    .menu-item:active {{
        transform: scale(0.94);
        filter: brightness(1.2);
    }}

    /* 카드 텍스트 (흰색 고정) */
    .menu-text {{
        color: #FFFFFF !important;
        font-size: 19px;
        font-weight: 800;
        letter-spacing: -0.5px;
        word-break: keep-all;
        line-height: 1.3;
        display: block !important;
        visibility: visible !important;
    }}

    /* 하단 알림바 */
    .bottom-notice {{
        background: #FFFFFF !important;
        border-radius: 50px;
        padding: 10px 20px;
        display: flex;
        align-items: center;
        margin: 20px auto;
        max-width: 470px;
    }}
    .badge {{
        background: #FF0000 !important;
        color: white !important;
        border-radius: 20px;
        padding: 2px 12px;
        font-weight: bold;
        font-size: 14px;
        margin-right: 15px;
    }}
    .notice-text {{ color: #333333 !important; font-weight: 600; font-size: 15px; }}

    /* 불필요한 UI 제거 */
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {{
        display: none !important;
    }}
    .block-container {{ padding: 0 !important; }}
    </style>

    <div class="custom-header">
        <div>
            <div class="brand-name">동네비서 😊</div>
            <div class="weather">소상공인을 위한 AI 스마트 관리</div>
        </div>
        <div class="time-section">
            <div class="current-time">{time_str}</div>
            <div class="current-date">{date_str}</div>
        </div>
    </div>

    <div class="menu-grid">
        {cards_html}
    </div>

    <div class="bottom-notice">
        <span class="badge">New!</span>
        <span class="notice-text">동네비서 2.0 업그레이드 완료</span>
    </div>
""", unsafe_allow_html=True)
