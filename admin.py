"""
동네비서 - 관리자 페이지
똑똑한 AI 이웃

권한별 메뉴 분리 버전
- 슈퍼 관리자: 가맹점 목록 조회, ID/비번 관리, 포인트 충전/관리, 신규 가맹점 등록/삭제
- 가맹점 사장님: 주문 내역, 프린터 설정, QR코드 생성, 메뉴 수정, 포인트 확인
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import qrcode
import io
import time
import os

# 커스텀 모듈 임포트
from db_manager import (
    get_all_stores, get_store, save_store, delete_store,
    get_all_orders, get_orders_by_store, update_order_status,
    get_settings, save_settings, initialize_sheets,
    verify_store_login,
    validate_password_length, hash_password, MIN_PASSWORD_LENGTH,
    verify_master_password, save_master_password, BUSINESS_CATEGORIES,
    update_store_points
)
from sms_manager import validate_phone_number
from printer_manager import test_printer_connection, ESCPOS_AVAILABLE
from pwa_helper import inject_pwa_tags, show_install_prompt, get_pwa_css

# ==========================================
# 🔑 마스터 관리자 설정
# ==========================================
MASTER_ID = "master"  # 슈퍼 관리자 ID

# ==========================================
# 🎨 페이지 설정
# ==========================================
st.set_page_config(
    page_title="동네비서 - 관리자",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS 스타일 - 글로벌 투명 유리 보라 테마 적용
st.markdown("""
<style>
/* 1. 글로벌 레이아웃 및 배경 */
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

html, body, [data-testid="stAppViewContainer"] {
    background-image: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), 
                      url('https://images.unsplash.com/photo-1514565131-fce0801e5785?auto=format&fit=crop&q=80&w=2000') !important;
    background-size: cover !important;
    background-position: center !important;
    background-attachment: fixed !important;
    font-family: 'Pretendard', sans-serif !important;
}

/* 2. 모든 컨테이너 및 카드에 유리 효과 적용 */
[data-testid="stExpander"], div[data-testid="stForm"], .stContainer, div.stBlock, [data-testid="stVerticalBlock"] > div > div {
    background-color: rgba(180, 150, 255, 0.2) !important;
    backdrop-filter: blur(15px) !important;
    border-radius: 25px !important;
    border: 1px solid rgba(200, 180, 255, 0.4) !important;
    padding: 20px !important;
    margin-bottom: 20px !important;
    color: #000000 !important;
}

/* 3. 모든 버튼 스타일 통일 (초투명 보라 유리) */
div.stButton > button, div.stFormSubmitButton > button, div.stDownloadButton > button {
    background-color: rgba(180, 150, 255, 0.3) !important;
    backdrop-filter: blur(10px) !important;
    border-radius: 20px !important;
    border: 1px solid rgba(200, 180, 255, 0.5) !important;
    color: #000000 !important;
    font-weight: bold !important;
    transition: all 0.3s ease !important;
    width: 100% !important;
    height: 60px !important;
}

div.stButton > button:hover {
    background-color: rgba(180, 150, 255, 0.5) !important;
    transform: translateY(-3px) !important;
    box-shadow: 0 10px 20px rgba(0,0,0,0.2) !important;
}

/* 4. 입력창 스타일 */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
    background-color: rgba(255, 255, 255, 0.9) !important;
    color: #000000 !important;
    border-radius: 15px !important;
    border: 1px solid rgba(180, 150, 255, 0.3) !important;
    font-weight: bold !important;
    padding: 15px !important;
}

/* 5. 텍스트 가독성 */
h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stMetric, .stDataFrame {
    color: #000000 !important;
    font-weight: bold !important;
    text-shadow: 0 1px 2px rgba(255,255,255,0.5) !important;
}

/* 메인 슬로건 등 흰색이 필요한 부분 예외 처리 */
.app-card h1, .app-card p {
    color: #FFFFFF !important;
    text-shadow: 0 2px 10px rgba(0,0,0,0.8) !important;
}

/* 6. 사이드바 스타일 (유리 효과 유지) */
[data-testid="stSidebar"] {
    background-color: transparent !important;
}

[data-testid="stSidebar"] > div:first-child {
    background-color: rgba(255, 255, 255, 0.1) !important;
    backdrop-filter: blur(20px) !important;
    margin: 10px !important;
    border-radius: 30px !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

/* 스트림릿 기본 요소 숨기기 */
header, footer, #MainMenu {visibility: hidden; display: none !important;}
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}

/* 7. 상단 고정 레이아웃 */
.top-right-logo {
    position: fixed;
    top: 20px;
    right: 20px;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    border: 2px solid rgba(255, 255, 255, 0.5);
    background: rgba(180, 150, 255, 0.2);
    backdrop-filter: blur(10px);
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
}

.top-left-user-card {
    position: fixed;
    top: 20px;
    left: 20px;
    padding: 10px 18px;
    background: rgba(180, 150, 255, 0.3);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(200, 180, 255, 0.5);
    border-radius: 15px;
    color: #000000;
    font-weight: bold;
    font-size: 14px;
    z-index: 9999;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
}
</style>

<div class="top-right-logo"></div>
""", unsafe_allow_html=True)

# ==========================================
# 세션 상태 초기화
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_type" not in st.session_state:
    st.session_state.user_type = None  # "master" 또는 "store"
if "store_id" not in st.session_state:
    st.session_state.store_id = None
if "store_info" not in st.session_state:
    st.session_state.store_info = {}

# 0. 왼쪽 상단 사용자 카드 (로그인 시 노출)
if st.session_state.logged_in:
    user_name = st.session_state.user_type == "master" and "총관리자" or st.session_state.store_info.get('name', '사장님')
    points_info = ""
    if st.session_state.user_type == "store":
        si = get_store(st.session_state.store_id)
        if si: points_info = f"<br>💎 잔액: {si.get('points', 0):,}원"
    
    st.markdown(f"""
    <div class="top-left-user-card">
        👤 {user_name}님{points_info}
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 통합 로그인 화면
# ==========================================
if not st.session_state.logged_in:
    st.markdown('<div style="height: 15vh;"></div>', unsafe_allow_html=True)
    with st.container():
        st.markdown("<h1 style='text-align:center; color:white !important;'>동네비서 AI 관리센터</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:rgba(255,255,255,0.8) !important;'>통합 관리자 로그인</p>", unsafe_allow_html=True)
        
        u_id = st.text_input("아이디", placeholder="ID")
        u_pw = st.text_input("비밀번호", type="password", placeholder="Password")
        
        if st.button("스마트 로그인", key="login_btn"):
            if u_id == "master":
                if verify_master_password(u_pw):
                    st.session_state.logged_in = True
                    st.session_state.user_type = "master"
                    st.rerun()
                else:
                    st.error("비밀번호 오류")
            else:
                success, msg, info = verify_store_login(u_id, u_pw)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user_type = "store"
                    st.session_state.store_id = u_id
                    st.session_state.store_info = info
                    st.rerun()
                else:
                    st.error(msg)
    st.stop()

# = :::::::::::::::::::::::::::::::::::::: =
# 관리자 메인 화면
# = :::::::::::::::::::::::::::::::::::::: =
if st.session_state.user_type == "master":
    st.markdown("""
    <div class="app-card" style="background: linear-gradient(135deg, #7850FF 0%, #B496FF 100%); color: white; padding: 30px; border-radius: 20px; margin-bottom: 30px;">
        <h1 style="color: white !important;">본사 마스터 대시보드</h1>
        <p>가맹점 포인트 및 시스템 통합 관리</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["포인트 관리", "가맹점 목록", "신규 등록", "설정"])

    with tab1:
        st.markdown("### 💎 포인트 통합 관리")
        stores = get_all_stores()
        if stores:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("전체 가맹점", f"{len(stores)}개")
            with col2:
                total_pts = sum([int(s.get('points', 0) or 0) for s in stores.values()])
                st.metric("총 유통 포인트", f"{total_pts:,}원")
            
            with st.container():
                st.markdown("#### ⚡ 빠른 포인트 충전")
                options = [f"{s.get('name')} ({sid})" for sid, s in stores.items()]
                sel = st.selectbox("가맹점 선택", ["선택하세요..."] + options)
                amt = st.number_input("충전 금액", min_value=0, step=1000, value=10000)
                if st.button("즉시 충전"):
                    if sel != "선택하세요...":
                        tid = sel.split("(")[-1].rstrip(")")
                        if update_store_points(tid, amt):
                            st.success("충전 완료")
                            st.rerun()

    with tab2:
        st.markdown("### 🏢 가맹점 목록")
        stores = get_all_stores()
        if stores:
            data = []
            for sid, info in stores.items():
                data.append({
                    "ID": sid,
                    "가게명": info.get('name'),
                    "점주": info.get('owner_name'),
                    "연락처": info.get('phone'),
                    "포인트": f"{int(info.get('points', 0) or 0):,}원"
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True)

    with tab3:
        st.markdown("### 📝 신규 가맹점 등록")
        with st.form("new_store"):
            c1, c2 = st.columns(2)
            with c1:
                nid = st.text_input("아이디*")
                npw = st.text_input("비밀번호*", type="password")
                nname = st.text_input("가게명*")
            with c2:
                nowner = st.text_input("대표자명*")
                nphone = st.text_input("연락처")
                npts = st.number_input("초기 포인트", value=1000)
            
            if st.form_submit_button("등록하기"):
                if nid and npw and nname and nowner:
                    if save_store(nid, {'password': npw, 'name': nname, 'owner_name': nowner, 'phone': nphone, 'points': npts}):
                        st.success("등록 완료")
                        st.rerun()

    with tab4:
        if st.button("로그아웃"):
            st.session_state.logged_in = False
            st.rerun()

else:
    # 가맹점 사장님 화면
    store_info = get_store(st.session_state.store_id)
    st.markdown(f"""
    <div class="app-card" style="background: linear-gradient(135deg, #1D3557 0%, #457B9D 100%); color: white; padding: 30px; border-radius: 20px; margin-bottom: 30px;">
        <h1 style="color: white !important;">{store_info.get('name')} 사장님 대시보드</h1>
        <p>실시간 주문 및 매장 관리 시스템</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["주문 관리", "매장 설정", "시스템"])
    
    with tab1:
        st.markdown("### 📦 실시간 주문 내역")
        orders = get_orders_by_store(st.session_state.store_id)
        if orders:
            for o in sorted(orders, key=lambda x: x.get('order_time', ''), reverse=True):
                with st.container():
                    st.write(f"**주문 #{o.get('order_id')}** ({o.get('order_time')})")
                    st.write(f"내용: {o.get('order_content')}")
                    st.write(f"상태: {o.get('status')}")
                    if st.button("완료 처리", key=f"done_{o.get('order_id')}"):
                        update_order_status(o.get('order_id'), "완료")
                        st.rerun()
        else:
            st.info("주문 내역이 없습니다.")

    with tab2:
        st.markdown("### ⚙️ 매장 정보 수정")
        with st.form("edit_store"):
            ename = st.text_input("가게명", value=store_info.get('name'))
            ephone = st.text_input("연락처", value=store_info.get('phone'))
            einfo = st.text_area("영업정보", value=store_info.get('info'))
            if st.form_submit_button("저장하기"):
                store_info.update({'name': ename, 'phone': ephone, 'info': einfo})
                if save_store(st.session_state.store_id, store_info):
                    st.success("저장 완료")
                    st.rerun()

    with tab3:
        if st.button("로그아웃"):
            st.session_state.logged_in = False
            st.rerun()
