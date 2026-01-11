import streamlit as st
from datetime import datetime

# 1. 전체 페이지 설정 및 불필요한 요소 제거
st.set_page_config(page_title="동네비서", layout="centered")

# 2. 단일 HTML/CSS 블록으로 디자인과 그리드를 한 번에 출력
# (이렇게 해야 Streamlit이 레이아웃을 깨뜨리지 않습니다)

now = datetime.now()
time_str = now.strftime('%H : %M')
date_str = now.strftime('%Y. %m. %d') + f" ({['월','화','수','목','금','토','일'][now.weekday()]})"

# 메뉴 데이터
menus = [
    {"title": "매장 예약", "color": "#E11E5A"}, # 장미빛
    {"title": "택배 접수", "color": "#2E7D32"}, # 초록
    {"title": "경영 분석", "color": "#1565C0"}, # 파랑
    {"title": "고객 명부", "color": "#EF6C00"}, # 오렌지
    {"title": "문자 발송", "color": "#6A1B9A"}, # 보라
    {"title": "주문 장부", "color": "#455A64"}, # 회색
    {"title": "정산 내역", "color": "#00838F"}, # 청록
    {"title": "매출 분석", "color": "#AD1457"}, # 진분홍
    {"title": "공지 사항", "color": "#F9A825"}, # 황금색
    {"title": "관리자 모드", "color": "#37474F"}  # 어두운 청회색
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
    /* 전체 배경 */
    .stApp {{
        background-color: #000000 !important;
    }}
    
    /* 상단 헤더 */
    .custom-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 20px 15px 10px 15px;
        color: white;
    }}
    .header-left {{ text-align: left; }}
    .header-right {{ text-align: right; }}
    .brand-name {{ font-size: 26px; font-weight: 900; margin-bottom: 5px; }}
    .weather {{ font-size: 14px; color: #AAAAAA; }}
    .current-time {{ font-size: 28px; font-weight: 700; }}
    .current-date {{ font-size: 14px; color: #AAAAAA; }}

    /* 그리드 컨테이너 */
    .menu-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        padding: 15px;
        max-width: 500px;
        margin: 0 auto;
    }}

    /* 카드 스타일 */
    .menu-item {{
        border-radius: 20px;
        aspect-ratio: 1.2 / 1;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        cursor: pointer;
        transition: transform 0.1s ease;
    }}
    .menu-item:active {{
        transform: scale(0.95);
        filter: brightness(1.1);
    }}

    /* 카드 텍스트 */
    .menu-text {{
        color: white !important;
        font-size: 20px;
        font-weight: 800;
        letter-spacing: -0.5px;
        word-break: keep-all;
    }}

    /* 하단 알림바 */
    .bottom-notice {{
        background: white;
        border-radius: 50px;
        padding: 10px 20px;
        display: flex;
        align-items: center;
        margin: 20px 15px;
        max-width: 470px;
        margin-left: auto;
        margin-right: auto;
    }}
    .badge {{
        background: #FF0000;
        color: white;
        border-radius: 20px;
        padding: 2px 12px;
        font-weight: bold;
        font-size: 14px;
        margin-right: 15px;
    }}
    .notice-text {{ color: #333333; font-weight: 600; font-size: 15px; }}

    /* 스트림릿 요소 제거 */
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {{
        display: none !important;
    }}
    .block-container {{ padding: 0 !important; }}
    </style>

    <div class="custom-header">
        <div class="header-left">
            <div class="brand-name">동네비서 😊</div>
            <div class="weather">서울 잠원동 6℃ 흐림 ☁️</div>
        </div>
        <div class="header-right">
            <div class="current-time">{time_str}</div>
            <div class="current-date">{date_str}</div>
        </div>
    </div>

    <div class="menu-grid">
        {cards_html}
    </div>

    <div class="bottom-notice">
        <span class="badge">New!</span>
        <span class="notice-text">동네비서 시스템 업데이트 완료!</span>
    </div>
""", unsafe_allow_html=True)
