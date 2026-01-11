import streamlit as st
from datetime import datetime

# ==========================================
# 동네비서 PREMIUM KIOSK V2.0 (FINAL)
# ==========================================

st.set_page_config(page_title="동네비서", layout="centered")

now = datetime.now()
time_str = now.strftime('%H:%M')
date_str = now.strftime('%Y. %m. %d') + f" ({['월','화','수','목','금','토','일'][now.weekday()]})"

# 동네비서 10개 핵심 메뉴 (고등학교 내용 완전 제거)
menus = [
    {"title": "매장 예약", "icon": "📅", "color": "#E11E5A"},
    {"title": "택배 접수", "icon": "📦", "color": "#2E7D32"},
    {"title": "고객 관리", "icon": "👥", "color": "#1565C0"},
    {"title": "주문 장부", "icon": "📋", "color": "#EF6C00"},
    {"title": "AI 상담원", "icon": "🤖", "color": "#6A1B9A"},
    {"title": "매출 통계", "icon": "📈", "color": "#AD1457"},
    {"title": "문자 발송", "icon": "💬", "color": "#00838F"},
    {"title": "정산 내역", "icon": "💰", "color": "#455A64"},
    {"title": "공지 사항", "icon": "📢", "color": "#F9A825"},
    {"title": "서비스 안내", "icon": "ℹ️", "color": "#37474F"}
]

# 카드 HTML 묶음 생성
cards_html = "".join([f"""
    <div class="card" style="background-color: {m['color']} !important;">
        <div class="card-icon">{m['icon']}</div>
        <div class="card-title">{m['title']}</div>
    </div>
""" for m in menus])

# 전체 레이아웃 (단일 Markdown으로 렌더링)
st.markdown(f"""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    html, body, .stApp {{
        background-color: #000000 !important;
        font-family: 'Pretendard', sans-serif !important;
    }}

    .block-container {{
        padding: 1.5rem 1rem !important;
        max-width: 500px !important;
        margin: 0 auto !important;
    }}

    .kiosk-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        padding: 10px 10px 30px 10px;
        color: white;
    }}

    .brand {{ font-size: 28px; font-weight: 900; }}
    .sub-brand {{ font-size: 14px; color: #888; margin-top: 5px; }}
    .time-info {{ text-align: right; }}
    .time {{ font-size: 32px; font-weight: 700; line-height: 1; }}
    .date {{ font-size: 14px; color: #888; margin-top: 5px; }}

    .grid-container {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
    }}

    .card {{
        border-radius: 20px;
        aspect-ratio: 1.3 / 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        cursor: pointer;
    }}

    .card-icon {{ font-size: 38px; margin-bottom: 8px; }}
    .card-title {{ color: white !important; font-size: 18px; font-weight: 800; }}

    .footer-bar {{
        background: white;
        border-radius: 100px;
        padding: 10px 20px;
        display: flex;
        align-items: center;
        margin-top: 25px;
    }}

    .badge {{
        background: #FF0000;
        color: white;
        font-size: 12px;
        font-weight: 900;
        padding: 2px 10px;
        border-radius: 50px;
        margin-right: 15px;
    }}

    .notice {{ color: #121212; font-size: 14px; font-weight: 600; }}

    /* Streamlit UI 제거 */
    header, footer, [data-testid="stHeader"], [data-testid="stToolbar"] {{
        display: none !important;
    }}
</style>

<div class="kiosk-header">
    <div>
        <div class="brand">동네비서 😊</div>
        <div class="sub-brand">AI 스마트 매장관리 시스템</div>
    </div>
    <div class="time-info">
        <div class="time">{time_str}</div>
        <div class="date">{date_str}</div>
    </div>
</div>

<div class="grid-container">
    {cards_html}
</div>

<div class="footer-bar">
    <span class="badge">NEW</span>
    <span class="notice">동네비서 프리미엄 대시보드가 활성화되었습니다.</span>
</div>
""", unsafe_allow_html=True)
