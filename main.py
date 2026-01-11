import streamlit as st
from datetime import datetime

# BUILD_VERSION: 20260111_1720_FINAL_REDEPLOY
# 10년차 개발자 자존심을 걸고 배포 지연 문제를 해결하기 위한 통합 코드입니다.

st.set_page_config(page_title="동네비서 KIOSK", layout="centered")

now = datetime.now()
time_str = now.strftime('%H:%M')
date_str = now.strftime('%Y. %m. %d') + f" ({['월','화','수','목','금','토','일'][now.weekday()]})"

# 메뉴 데이터 (10개 고정)
menus = [
    {"title": "매장 예약", "icon": "📅", "color": "#E11E5A"},
    {"title": "택배 접수", "icon": "📦", "color": "#2E7D32"},
    {"title": "고객 명부", "icon": "👥", "color": "#1565C0"},
    {"title": "주문 장부", "icon": "📋", "color": "#EF6C00"},
    {"title": "AI 상담원", "icon": "🤖", "color": "#6A1B9A"},
    {"title": "매출 통계", "icon": "📈", "color": "#AD1457"},
    {"title": "문자 발송", "icon": "💬", "color": "#00838F"},
    {"title": "정산 내역", "icon": "💰", "color": "#455A64"},
    {"title": "공지 사항", "icon": "📢", "color": "#F9A825"},
    {"title": "서비스 안내", "icon": "ℹ️", "color": "#37474F"}
]

# 모든 요소를 하나의 HTML 문자열로 결합 (레이아웃 깨짐 방지 핵심)
cards_html = "".join([f"""
    <div class="card">
        <div class="card-icon">{m['icon']}</div>
        <div class="card-title">{m['title']}</div>
    </div>
""" for m in menus])

full_ui_html = f"""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    .stApp {{
        background-color: #0A0A0B !important;
        font-family: 'Pretendard', sans-serif !important;
    }}

    .block-container {{
        padding: 1.5rem 1rem !important;
        max-width: 500px !important;
        margin: 0 auto !important;
    }}

    .kiosk-wrapper {{
        color: white;
    }}

    .kiosk-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        padding-bottom: 30px;
    }}

    .brand {{ font-size: 30px; font-weight: 900; letter-spacing: -1px; }}
    .brand span {{ color: #4D7CFF; }}
    .sub-title {{ font-size: 14px; color: #888; margin-top: 5px; }}

    .time-info {{ text-align: right; }}
    .time {{ font-size: 32px; font-weight: 700; line-height: 1; }}
    .date {{ font-size: 14px; color: #888; margin-top: 5px; }}

    .kiosk-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 15px;
    }}

    .card {{
        background: #1C1C1E;
        border-radius: 24px;
        padding: 25px 15px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        border: 1px solid rgba(255,255,255,0.05);
        transition: all 0.15s ease;
    }}

    .card-icon {{ font-size: 40px; margin-bottom: 12px; }}
    .card-title {{ font-size: 18px; font-weight: 700; color: #FFFFFF; }}

    .kiosk-footer {{
        margin-top: 30px;
        background: white;
        border-radius: 100px;
        padding: 12px 20px;
        display: flex;
        align-items: center;
    }}

    .badge {{
        background: #FF3B30;
        color: white;
        font-size: 12px;
        font-weight: 900;
        padding: 4px 12px;
        border-radius: 50px;
        margin-right: 15px;
    }}

    .notice-text {{ color: #121212; font-size: 15px; font-weight: 600; }}

    /* Streamlit UI Hiding */
    header, footer, [data-testid="stHeader"], [data-testid="stToolbar"] {{
        display: none !important;
    }}
</style>

<div class="kiosk-wrapper">
    <div class="kiosk-header">
        <div>
            <div class="brand" style="color: #FF3B30 !important;">동네비서 KIOSK v2<span>.</span></div>
            <div class="sub-title">전문가용 프리미엄 매장 관리 시스템</div>
        </div>
        <div class="time-info">
            <div class="time">{time_str}</div>
            <div class="date">{date_str}</div>
        </div>
    </div>
    
    <div class="kiosk-grid">
        {cards_html}
    </div>

    <div class="kiosk-footer">
        <span class="badge">SYSTEM</span>
        <span class="notice-text">동네비서 프리미엄 대시보드 활성화</span>
    </div>
</div>
"""

st.markdown(full_ui_html, unsafe_allow_html=True)
