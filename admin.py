"""
🏘️ 동네비서 - 관리자 페이지
똑똑한 AI 이웃

권한별 메뉴 분리 버전
- 슈퍼 관리자: 가맹점 목록 조회, ID/비번 관리, 가맹비 납부 체크, 신규 가맹점 등록/삭제
- 가맹점 사장님: 주문 내역, 프린터 설정, QR코드 생성, 메뉴 수정
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import qrcode
import io

# 커스텀 모듈 임포트
from db_manager import (
    get_all_stores, get_store, save_store, delete_store,
    get_all_orders, get_orders_by_store, update_order_status,
    get_settings, save_settings, initialize_sheets,
    update_store_status, verify_store_login, update_billing_info,
    validate_password_length, hash_password, MIN_PASSWORD_LENGTH,
    verify_master_password, save_master_password, BUSINESS_CATEGORIES
)
from sms_manager import send_invitation_sms, validate_phone_number
from printer_manager import test_printer_connection, ESCPOS_AVAILABLE
from pwa_helper import inject_pwa_tags, show_install_prompt, get_pwa_css
from toss_payments import (
    issue_billing_key_with_card, execute_billing_payment,
    get_bank_transfer_info, generate_order_id,
    calculate_expiry_date, calculate_next_payment_date,
    is_expired, get_toss_credentials
)

# ==========================================
# 🔑 마스터 관리자 설정
# ==========================================
MASTER_ID = "master"  # 슈퍼 관리자 ID
# 마스터 비밀번호는 Google Sheets에서 관리 (verify_master_password 함수 사용)

# ==========================================
# 🎨 페이지 설정
# ==========================================
st.set_page_config(
    page_title="동네비서 - 관리자",
    page_icon="🏘️",
    layout="wide"
)

# CSS 스타일 - 삼성 키오스크 스타일 (Universal Kiosk UI)
st.markdown("""
<style>
/* 1. 기본 배경 및 폰트 */
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

html, body, [data-testid="stAppViewContainer"] {
    background-color: #F8F9FA !important;
    color: #1D3557 !important;
    font-family: 'Pretendard', sans-serif !important;
}

/* 스트림릿 UI 완벽 제거 (모바일 포함) */
header, footer, #MainMenu {visibility: hidden; display: none !important;}
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
[data-testid="stStatusWidget"], #manage-app-button, .stDeployButton {display: none !important;}
button[data-testid="stHeaderActionButton"] {display: none !important;}
div[data-testid="stStatusWidget"] {display: none !important;}
.viewerBadge_container__1QS1n {display: none !important;}
.stAppDeployButton {display: none !important;}

/* 서랍식 사이드바 (Kiosk Floating Drawer) 디자인 */
[data-testid="stSidebar"] {
    background-color: transparent !important;
    min-width: 400px !important;
}

[data-testid="stSidebar"] > div:first-child {
    background-color: #FFFFFF !important;
    margin: 20px !important;
    border-radius: 40px !important;
    height: calc(100vh - 40px) !important;
    box-shadow: 25px 0 60px rgba(0,0,0,0.15) !important;
    border: 1px solid #E9ECEF !important;
    overflow: hidden !important;
    position: relative !important;
}

/* 서랍 손잡이 (Drawer Handle) 시각화 */
[data-testid="stSidebar"] > div:first-child::after {
    content: "";
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    width: 6px;
    height: 60px;
    background: #E9ECEF;
    border-radius: 10px;
}

/* 사이드바 내부 버튼 스타일 (서랍 아이템 느낌) */
[data-testid="stSidebar"] .stButton > button {
    height: 70px !important;
    border-radius: 22px !important;
    font-size: 20px !important;
    font-weight: 700 !important;
    margin-bottom: 12px !important;
    text-align: left !important;
    padding-left: 25px !important;
    justify-content: flex-start !important;
    background-color: #F8F9FA !important;
    color: #1D3557 !important;
    border: 2px solid transparent !important;
    transition: all 0.2s ease !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #FFFFFF !important;
    border-color: #1D3557 !important;
    color: #1D3557 !important;
    box-shadow: 0 10px 20px rgba(0,0,0,0.05) !important;
    transform: translateX(5px) !important;
}

/* 2. 타이포그래피 */
.stMarkdown p, .stMarkdown span, label, .stMetric {
    color: #1D3557 !important;
    font-size: 18px !important;
    font-weight: 600 !important;
}

h1, h2, h3 { font-weight: 900 !important; color: #1D3557 !important; }

/* 3. 키오스크형 버튼 스타일 */
.stButton>button, .stFormSubmitButton>button {
    width: 100% !important;
    height: 80px !important;
    font-size: 24px !important;
    font-weight: 900 !important;
    background-color: #1D3557 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 0px !important;
    margin-bottom: 2px !important;
    transition: all 0.2s ease !important;
}

.stButton>button:hover {
    background-color: #0B1D33 !important;
}

/* 4. 관리자 카드 스타일 */
.metric-card, .stats-card, .order-card, .login-card, .app-card {
    background-color: transparent !important;
    border: none !important;
    padding: 20px 0 !important;
    margin-bottom: 25px !important;
}

/* 5. 입력창 스타일 */
[data-testid="stTextInput"] > div[data-baseweb="input"],
[data-testid="stSelectbox"] > div[data-baseweb="select"] {
    border: 2px solid #E9ECEF !important;
    border-radius: 18px !important;
    padding: 10px !important;
    background-color: #F8F9FA !important;
}

/* 탭 디자인 */
.stTabs [data-baseweb="tab"] {
    font-weight: 800 !important;
    font-size: 18px !important;
    padding: 15px 25px !important;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 세션 상태 초기화
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_type" not in st.session_state:
    st.session_state.user_type = None  # "master" 또는 "store"
if "store_id" not in st.session_state:
    st.session_state.store_id = None
if "store_info" not in st.session_state:
    st.session_state.store_info = {}

# = :::::::::::::::::::::::::::::::::::::: =
# 🏰 키오스크 서랍식 메뉴 (Sidebar Drawer)
# = :::::::::::::::::::::::::::::::::::::: =
with st.sidebar:
    # 로고 영역 (텍스트 중심의 묵직한 디자인)
    st.markdown("""
    <div style="text-align: center; padding: 60px 0 50px 0;">
        <h1 style="font-size: 38px; margin-bottom: 0px; color: #0B1D33 !important; font-weight: 950; letter-spacing: 4px; text-indent: 4px;">동네비서ai본부</h1>
        <div style="width: 80%; height: 2px; background: #0B1D33; margin: 30px auto; opacity: 0.3;"></div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.logged_in:
        if st.session_state.user_type == "master":
            st.markdown("### 👑 마스터 도구")
            if st.button("🔧 시트 데이터 초기화", use_container_width=True):
                if initialize_sheets(): st.success("초기화 완료")
        else:
            st.markdown(f"### 🏪 {st.session_state.store_info.get('name', '')}")
            st.info("사장님 전용 관리 모드")

        st.markdown("---")
        if st.button("🚪 시스템 로그아웃", use_container_width=True):
            st.session_state.logged_in = False; st.rerun()
    else:
        st.info("로그인이 필요합니다.")

    st.markdown("---")
    st.caption("© 2025 동네비서 AI Platform")

# ==========================================
# 🎁 홍보 문구 설정 (나중에 관리자가 수정 가능하도록)
# ==========================================
PROMO_TITLE = "🚀 동네비서에 가입하세요!"
PROMO_SUBTITLE = "🎁 지금 가입하면 한 달 무료 체험 혜택 제공!"
PROMO_BADGE = "✨ 월 이용료 0원으로 시작하기 ✨"

# ==========================================
# 📱 PWA 설정 적용
# ==========================================
inject_pwa_tags()  # PWA 메타 태그 주입
st.markdown(get_pwa_css(), unsafe_allow_html=True)  # PWA 최적화 CSS

# AI 직원 24시간 근무중 배지 CSS
st.markdown("""
<style>
    .ai-badge-container {
        display: flex;
        justify-content: center;
        margin-bottom: 25px;
    }
    .ai-working-badge {
        display: inline-flex;
        align-items: center;
        background: #FFFFFF;
        color: #1D3557;
        padding: 12px 28px;
        border-radius: 40px;
        font-weight: 800;
        font-size: 1.1rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.06);
        border: 2px solid #E9ECEF;
    }
    .ai-working-badge .ai-dot {
        width: 12px;
        height: 12px;
        background: #4CAF50;
        border-radius: 50%;
        margin-right: 12px;
        animation: aiPulse 1.5s ease-in-out infinite;
    }
    .ai-working-badge .ai-icon {
        margin-right: 10px;
        font-size: 1.3rem;
    }
    @keyframes aiPulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.8); }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 로그인 화면
# ==========================================
if not st.session_state.logged_in:
    # 🤖 AI 직원 배지 표시
    st.markdown("""
    <div class="ai-badge-container">
        <div class="ai-working-badge">
            <span class="ai-dot"></span>
            <span class="ai-icon">&#129302;</span>
            AI 직원 24시간 근무중
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 🎁 홍보 배너 표시
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1D3557 0%, #457B9D 100%);
                padding: 40px; border-radius: 28px; text-align: center; color: white;
                margin-bottom: 40px; box-shadow: 0 15px 35px rgba(29, 53, 87, 0.2);">
        <h1 style="color: white !important; margin-bottom: 10px;">{PROMO_TITLE}</h1>
        <p style="font-size: 20px; opacity: 0.9;">{PROMO_SUBTITLE}</p>
        <div style="display: inline-block; background: rgba(255,255,255,0.2); 
                    padding: 8px 24px; border-radius: 40px; margin-top: 15px; font-weight: 800;">
            {PROMO_BADGE}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("# 🏘️ 동네비서 관리자")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # 로그인 유형 선택
        login_type = st.radio(
            "로그인 유형을 선택하세요",
            ["🏢 슈퍼 관리자 (마스터)", "🏪 가맹점 사장님"],
            horizontal=True
        )

        st.markdown("---")

        if "슈퍼 관리자" in login_type:
            # 마스터 로그인
            st.markdown("### 🏢 슈퍼 관리자 로그인")
            st.markdown('<div class="login-card">', unsafe_allow_html=True)

            master_pw = st.text_input(
    "마스터 비밀번호",
    type="password",
    placeholder="마스터 비밀번호 입력")

            if st.button("🚀 마스터 로그인", use_container_width=True,
                        type="primary"):
                if verify_master_password(master_pw):
                    st.session_state.logged_in = True
                    st.session_state.user_type = "master"
                    st.session_state.store_id = None
                    st.session_state.store_info = None
                    st.success("✅ 슈퍼 관리자로 로그인되었습니다!")
                st.rerun()
            else:
                st.error("❌ 비밀번호가 틀렸습니다.")

            st.markdown('</div>', unsafe_allow_html=True)
            st.caption("💡 슈퍼 관리자는 전체 가맹점을 관리할 수 있습니다.")

        else:
            # 가맹점 로그인
            st.markdown("### 🏪 가맹점 사장님 로그인")
            st.markdown('<div class="login-card">', unsafe_allow_html=True)

            store_id = st.text_input("가게 아이디", placeholder="가맹점 ID 입력")
            store_pw = st.text_input(
    "비밀번호", type="password", placeholder="비밀번호 입력")

            if st.button("🚀 로그인", use_container_width=True, type="primary"):
                if store_id and store_pw:
                    store_info = verify_store_login(store_id, store_pw)
                    if store_info:
                        st.session_state.logged_in = True
                        st.session_state.user_type = "store"
                        st.session_state.store_id = store_id
                        st.session_state.store_info = store_info
                        st.success(
    f"✅ {
        store_info.get(
            'name',
            store_id)} 사장님 환영합니다!")
                        st.rerun()
                    else:
                        st.error("❌ 아이디 또는 비밀번호가 틀렸습니다.")
                else:
                    st.warning("아이디와 비밀번호를 모두 입력해주세요.")

            st.markdown('</div>', unsafe_allow_html=True)
            st.caption("💡 가맹점 사장님은 본인 가게만 관리할 수 있습니다.")

    st.stop()

# ==========================================
# 👑 슈퍼 관리자 전용 페이지
# ==========================================
if st.session_state.user_type == "master":
    st.markdown("""
    <div class="app-card" style="background: linear-gradient(135deg, #1D3557 0%, #457B9D 100%); color: white; margin-bottom: 40px;">
        <h1 style="color: white !important; margin: 0;">👑 슈퍼 관리자 대시보드</h1>
        <p style="opacity: 0.9; margin-top: 10px;">전체 가맹점 및 시스템 통합 관리 모드입니다.</p>
    </div>
    """, unsafe_allow_html=True)

    # 탭 구성 - 슈퍼 관리자용
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 가맹점 목록/관리",
        "💰 가맹비 관리",
        "➕ 신규 가맹점 등록",
        "🔐 비밀번호 변경"
    ])

    # ==========================================
    # 📋 탭1: 가맹점 목록/관리
    # ==========================================
    with tab1:
        st.markdown("### 📋 전체 가맹점 목록")

        try:
            stores = get_all_stores()
        except Exception as e:
            st.error(f"❌ 데이터 로드 실패: {e}")
            stores = {}

        # 통계 카드
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🏪 총 가맹점", f"{len(stores)}개")
        with col2:
            paid = len([s for s in stores.values() if s.get('status') == '납부'])
            st.metric("✅ 가맹비 납부", f"{paid}개")
        with col3:
            unpaid = len([s for s in stores.values() if s.get('status') != '납부'])
            st.metric("❌ 미납", f"{unpaid}개")
        with col4:
            printer_set = len([s for s in stores.values() if s.get('printer_ip')])
            st.metric("🖨️ 프린터 설정됨", f"{printer_set}개")

        st.markdown("---")

        if stores:
            # DataFrame 생성
            table_data = []
            for store_id, info in stores.items():
                status = info.get('status', '미납')
                status_html = "✅ 납부" if status == '납부' else "❌ 미납"
                category_key = info.get('category', 'restaurant')
                category_info = BUSINESS_CATEGORIES.get(category_key, BUSINESS_CATEGORIES.get('other', {}))
                category_name = category_info.get('name', '기타')

                table_data.append({
                    "아이디": store_id if store_id else "(빈값)",
                    "업종": category_name,
                    "가게이름": info.get('name', '-'),
                    "연락처": info.get('phone', '-'),
                    "가맹비상태": status_html,
                    "프린터IP": info.get('printer_ip', '미설정')
                })

            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("---")

            # 가게 삭제
            st.markdown("### 🗑️ 가맹점 삭제")
            delete_options = [f"{stores[sid].get('name', '이름없음')} ({sid})" for sid in stores.keys()]

            if delete_options:
                selected_delete = st.selectbox(
                    "🏪 삭제할 가맹점 선택",
                    options=["선택하세요..."] + delete_options,
                    key="delete_store"
                )

                if selected_delete and selected_delete != "선택하세요...":
                    store_id_to_delete = selected_delete.split("(")[-1].rstrip(")")
                    store_name_to_delete = stores.get(store_id_to_delete, {}).get('name', '이름없음')

                    st.error(f"⚠️ 정말로 '{store_name_to_delete}' 가맹점을 삭제하시겠습니까?")

                    confirm_delete = st.checkbox(
                        f"'{store_name_to_delete}' 삭제에 동의합니다.",
                        key=f"confirm_{store_id_to_delete}"
                    )

                    if st.button("🗑️ 삭제", disabled=not confirm_delete):
                        if delete_store(store_id_to_delete):
                            st.success(f"✅ 삭제 완료!")
                            st.rerun()
                        else:
                            st.error("❌ 삭제 실패")

            st.markdown("---")

            # ID/비밀번호 수정
            st.markdown("### 🔑 가맹점 정보 수정")
            edit_options = [f"{sid} ({stores[sid].get('name', '')})" for sid in stores.keys()]
            selected_edit = st.selectbox("수정할 가맹점", edit_options, key="edit_store")

            if selected_edit:
                edit_store_id = selected_edit.split(" (")[0]
                edit_store_info = stores.get(edit_store_id, {})

                col1, col2 = st.columns(2)
                with col1:
                    new_password = st.text_input(
                        f"새 비밀번호 (최소 {MIN_PASSWORD_LENGTH}자)",
                        type="password",
                        placeholder="변경시에만 입력"
                    )
                with col2:
                    new_name = st.text_input("가게 이름", value=edit_store_info.get('name', ''))

                if st.button("💾 저장", key="save_edit"):
                    if new_password:
                        pw_valid, pw_msg = validate_password_length(new_password)
                        if not pw_valid:
                            st.error(f"❌ {pw_msg}")
                            st.stop()
                        edit_store_info['password'] = new_password

                    edit_store_info['name'] = new_name
                    encrypt_pw = bool(new_password)

                    if save_store(edit_store_id, edit_store_info, encrypt_password=encrypt_pw):
                        st.success("✅ 저장 완료!")
                        st.rerun()
                    else:
                        st.error("❌ 저장 실패")
        else:
            st.info("📭 등록된 가맹점이 없습니다.")

    # ==========================================
    # 💰 탭2: 가맹비 관리
    # ==========================================
    with tab2:
        st.markdown("### 💰 가맹비 납부 관리")

        try:
            stores = get_all_stores()
        except Exception as e:
            st.error(f"❌ 데이터 로드 실패: {e}")
            stores = {}

        if stores:
            for store_id, info in stores.items():
                store_name = info.get('name', store_id)
                current_status = info.get('status', '미납')

                col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1.5])

                with col1:
                    st.markdown(f"**🏪 {store_name}**")
                    st.caption(f"ID: {store_id}")

                with col2:
                    if current_status == '납부':
                        st.success("✅ 납부완료")
                    else:
                        st.error("❌ 미납")

                with col3:
                    if st.button("✅ 납부", key=f"pay_{store_id}"):
                        if update_store_status(store_id, '납부'):
                            st.rerun()

                with col4:
                    if st.button("❌ 미납", key=f"unpay_{store_id}"):
                        if update_store_status(store_id, '미납'):
                            st.rerun()

                st.markdown("---")
        else:
            st.info("📭 등록된 가맹점이 없습니다.")

    # ==========================================
    # ➕ 탭3: 신규 가맹점 등록
    # ==========================================
    with tab3:
        st.markdown("### ➕ 신규 가맹점 등록")

        # 업종 선택
        st.markdown("#### 🏢 업종 선택")
        category_options = {k: v['name'] for k, v in BUSINESS_CATEGORIES.items()}
        new_category = st.selectbox(
            "업종",
            options=list(category_options.keys()),
            format_func=lambda x: category_options[x]
        )

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            new_store_id = st.text_input("가맹점 ID *")
            new_store_password = st.text_input("비밀번호 *", type="password")
            new_store_name = st.text_input("가게 이름 *")
        with col2:
            new_store_phone = st.text_input("연락처")
            new_store_info = st.text_input("영업 정보")
            new_store_status = st.selectbox("가맹비 상태", ["미납", "납부"])

        if st.button("➕ 등록하기", type="primary"):
            if not new_store_id or not new_store_password or not new_store_name:
                st.error("❌ 필수 항목을 입력하세요!")
            else:
                pw_valid, pw_msg = validate_password_length(new_store_password)
                if not pw_valid:
                    st.error(f"❌ {pw_msg}")
                else:
                    existing = get_all_stores()
                    if new_store_id in existing:
                        st.error("❌ 이미 존재하는 ID입니다!")
                    else:
                        from datetime import timedelta
                        expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

                        store_data = {
                            'password': new_store_password,
                            'name': new_store_name,
                            'phone': new_store_phone,
                            'info': new_store_info,
                            'menu_text': '',
                            'printer_ip': '',
                            'img_files': '',
                            'status': new_store_status,
                            'billing_key': '',
                            'expiry_date': expiry,
                            'payment_status': '무료체험',
                            'next_payment_date': '',
                            'category': new_category
                        }

                        if save_store(new_store_id, store_data):
                            st.success(f"✅ '{new_store_name}' 등록 완료!")
                            st.balloons()
                        else:
                            st.error("❌ 등록 실패")

    # ==========================================
    # 🔐 탭4: 비밀번호 변경
    # ==========================================
    with tab4:
        st.markdown("### 🔐 마스터 비밀번호 변경")

        current_pw = st.text_input("현재 비밀번호", type="password")
        new_pw = st.text_input("새 비밀번호", type="password")
        confirm_pw = st.text_input("새 비밀번호 확인", type="password")

        if st.button("🔐 변경하기"):
            if not current_pw or not new_pw or not confirm_pw:
                st.error("❌ 모든 항목을 입력하세요!")
            elif new_pw != confirm_pw:
                st.error("❌ 새 비밀번호가 일치하지 않습니다!")
            elif not verify_master_password(current_pw):
                st.error("❌ 현재 비밀번호가 틀립니다!")
            else:
                pw_valid, pw_msg = validate_password_length(new_pw)
                if not pw_valid:
                    st.error(f"❌ {pw_msg}")
                else:
                    if save_master_password(new_pw):
                        st.success("✅ 비밀번호가 변경되었습니다!")
                    else:
                        st.error("❌ 변경 실패")

# ==========================================
# 🏪 가맹점 사장님 전용 페이지
# ==========================================
else:
    store_id = st.session_state.store_id
    # 최신 store_info 다시 가져오기 (결제 상태 반영)
    store_info = get_store(store_id) or st.session_state.store_info
    store_name = store_info.get('name', store_id)

    st.markdown(f"## 🏪 {store_name} 관리 페이지")

    # = :::::::::::::::::::::::::::::::::::::: =
    # 🔗 내 가게 주문 링크 공유 섹션 (최상단 재배치)
    # = :::::::::::::::::::::::::::::::::::::: =
    try:
        # 주문 링크 생성 (main.py로 이동, store 파라미터 포함)
        base_url = st.secrets.get("APP_URL", "https://dnbsir.com")
        order_link = f"{base_url}?store={store_id}"
        
        st.markdown(f"""
        <div style="
            background: #FFFFFF;
            padding: 2.5rem;
            border-radius: 28px;
            margin: 1.5rem 0;
            box-shadow: 0 12px 30px rgba(0,0,0,0.04);
            border: 2px solid #E9ECEF;
        ">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px;">
                <div>
                    <div style="font-size: 1.5rem; font-weight: 900; color: #1D3557; margin-bottom: 8px;">
                        🔗 내 가게 주문 링크
                    </div>
                    <div style="font-size: 1rem; color: #6C757D;">
                        손님에게 이 링크를 보내면 바로 우리 가게 주문 화면으로 이동합니다.
                    </div>
                </div>
            </div>
            <div style="
                background: #F8F9FA;
                padding: 18px 25px;
                border-radius: 18px;
                margin-top: 25px;
                font-family: 'Pretendard', monospace;
                font-size: 1rem;
                color: #457B9D;
                word-break: break-all;
                border: 1px dashed #CED4DA;
            ">
                {order_link}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 복사 및 공유 버튼
        col_copy1, col_copy2 = st.columns(2)
        with col_copy1:
            copy_js = f"""
            <script>
            function copyOrderLink() {{
                navigator.clipboard.writeText("{order_link}").then(function() {{
                    alert("✅ 주문 링크가 복사되었습니다!\\n\\n손님에게 카카오톡, 문자 등으로 공유하세요.");
                }}, function(err) {{
                    prompt("링크를 복사하세요:", "{order_link}");
                }});
            }}
            </script>
            <button onclick="copyOrderLink()" style="
                width: 100%;
                padding: 15px 20px;
                font-size: 1.1rem;
                font-weight: 700;
                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                color: white;
                border: none;
                border-radius: 15px;
                cursor: pointer;
                box-shadow: 0 6px 20px rgba(17, 153, 142, 0.4);
                transition: transform 0.2s, box-shadow 0.2s;
            " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                📋 주문 링크 복사하기
            </button>
            """
            st.components.v1.html(copy_js, height=60)
        
        with col_copy2:
            st.markdown(f"""
            <a href="https://sharer.kakao.com/talk/friends/picker/link?url={order_link}&text={store_name}" target="_blank" style="
                display: block;
                width: 100%;
                padding: 15px 20px;
                font-size: 1.1rem;
                font-weight: 700;
                background: #FEE500;
                color: #3C1E1E;
                border: none;
                border-radius: 15px;
                cursor: pointer;
                box-shadow: 0 6px 20px rgba(254, 229, 0, 0.4);
                text-align: center;
                text-decoration: none;
                box-sizing: border-box;
            ">
                💬 카카오톡으로 공유
            </a>
            """, unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"⚠️ 주문 링크 생성 중 오류: {e}")

    st.markdown("---")

    # ==========================================
    # 📊 상단 대시보드 - 핵심 정보 요약
    # ==========================================
    st.markdown("")

    # 만료일 및 결제 상태 가져오기
    current_expiry = store_info.get('expiry_date', '')
    current_payment_status = store_info.get('payment_status', '미등록')
    current_billing_key = store_info.get('billing_key', '')

    # 대시보드 카드 4개
    col1, col2, col3, col4 = st.columns(4)

    # 오늘 주문 수 계산
    try:
        today_orders = get_orders_by_store(store_id)
        today = datetime.now().strftime("%Y-%m-%d")
        today_count = len([o for o in today_orders if o.get(
            'order_time', '').startswith(today)])
        today_revenue = sum([int(o.get('total_price', 0)) for o in today_orders if o.get(
            'order_time', '').startswith(today)])
    except:
        today_count = 0
        today_revenue = 0

    with col1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 1.2rem; border-radius: 15px; text-align: center; color: white;">
            <div style="font-size: 0.9rem; opacity: 0.9;">📦 오늘 주문</div>
            <div style="font-size: 2rem; font-weight: bold;">{today_count}건</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                    padding: 1.2rem; border-radius: 15px; text-align: center; color: white;">
            <div style="font-size: 0.9rem; opacity: 0.9;">💰 오늘 매출</div>
            <div style="font-size: 2rem; font-weight: bold;">{today_revenue:,}원</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        # 만료일 표시
        if current_expiry:
            if is_expired(current_expiry):
                expiry_bg = "linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%)"
                expiry_text = f"⚠️ 만료됨"
            else:
                expiry_bg = "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)"
                expiry_text = current_expiry
        else:
            expiry_bg = "linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)"
            expiry_text = "미설정"

        st.markdown(f"""
        <div style="background: {expiry_bg};
                    padding: 1.2rem; border-radius: 15px; text-align: center; color: white;">
            <div style="font-size: 0.9rem; opacity: 0.9;">📅 서비스 만료일</div>
            <div style="font-size: 1.3rem; font-weight: bold;">{expiry_text}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        # 결제 상태 표시
        if current_payment_status == '정상':
            status_bg = "linear-gradient(135deg, #56ab2f 0%, #a8e063 100%)"
            status_icon = "✅"
        elif current_payment_status == '무료체험':
            status_bg = "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)"
            status_icon = "🎁"
        elif current_payment_status == '실패':
            status_bg = "linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%)"
            status_icon = "❌"
        elif current_payment_status == '해지':
            status_bg = "linear-gradient(135deg, #bdc3c7 0%, #2c3e50 100%)"
            status_icon = "🚫"
        else:
            status_bg = "linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)"
            status_icon = "⚠️"

        st.markdown(f"""
        <div style="background: {status_bg};
                    padding: 1.2rem; border-radius: 15px; text-align: center; color: white;">
            <div style="font-size: 0.9rem; opacity: 0.9;">💳 결제 상태</div>
            <div style="font-size: 1.3rem; font-weight: bold;">{status_icon} {current_payment_status}</div>
        </div>
        """, unsafe_allow_html=True)

    # ==========================================
    # 📞 전화 후 자동 링크 발송 기능
    # ==========================================
    st.markdown("")
        
        with st.expander("📞 전화 받고 자동 링크 발송", expanded=False):
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%);
                padding: 1.2rem;
                border-radius: 15px;
                color: white;
                margin-bottom: 1rem;
            ">
                <div style="font-size: 1.1rem; font-weight: 700;">📞 전화 신호 3번 후 자동 링크 발송</div>
                <div style="font-size: 0.9rem; opacity: 0.95; margin-top: 5px;">
                    손님 전화번호 입력 → 시작 버튼 클릭 → 벨 3번 후 자동으로 주문 링크 문자 발송!
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 손님 전화번호 입력
            customer_phone_for_link = st.text_input(
                "📱 손님 전화번호",
                placeholder="01012345678",
                key="customer_phone_for_link",
                help="문자를 받을 손님의 전화번호를 입력하세요"
            )
            
            # 발송할 메시지 미리보기
            sms_message = f"""🍽️ {store_name}입니다!

아래 링크로 편리하게 주문하세요 👇

{order_link}

📞 문의: {store_info.get('phone', '')}"""
            
            with st.container():
                st.markdown("**📝 발송될 문자 미리보기:**")
                st.code(sms_message, language=None)
            
            # 전화 신호 시뮬레이션 및 발송 버튼
            if st.button("📞 전화 신호 시작 (3번 후 자동 발송)", key="btn_auto_send_link", use_container_width=True, type="primary"):
                if not customer_phone_for_link:
                    st.error("❌ 손님 전화번호를 입력해주세요!")
                elif len(customer_phone_for_link.replace("-", "").replace(" ", "")) < 10:
                    st.error("❌ 올바른 전화번호를 입력해주세요!")
                else:
                    # 전화번호 정리
                    clean_phone = customer_phone_for_link.replace("-", "").replace(" ", "")
                    
                    # 전화 신호 시뮬레이션
                    import time
                    
                    ring_placeholder = st.empty()
                    progress_bar = st.progress(0)
                    
                    # 벨 1번
                    ring_placeholder.markdown("""
                    <div style="text-align: center; padding: 20px;">
                        <div style="font-size: 4rem; animation: shake 0.5s infinite;">📞</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: #ff6b6b; margin-top: 10px;">
                            🔔 따르릉~ (1/3)
                        </div>
                    </div>
                    <style>
                        @keyframes shake {
                            0%, 100% { transform: rotate(-5deg); }
                            50% { transform: rotate(5deg); }
                        }
                    </style>
                    """, unsafe_allow_html=True)
                    progress_bar.progress(33)
                    time.sleep(1.5)
                    
                    # 벨 2번
                    ring_placeholder.markdown("""
                    <div style="text-align: center; padding: 20px;">
                        <div style="font-size: 4rem; animation: shake 0.5s infinite;">📞</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: #feca57; margin-top: 10px;">
                            🔔 따르릉~ (2/3)
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    progress_bar.progress(66)
                    time.sleep(1.5)
                    
                    # 벨 3번
                    ring_placeholder.markdown("""
                    <div style="text-align: center; padding: 20px;">
                        <div style="font-size: 4rem; animation: shake 0.5s infinite;">📞</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: #38ef7d; margin-top: 10px;">
                            🔔 따르릉~ (3/3)
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    progress_bar.progress(100)
                    time.sleep(1)
                    
                    # 문자 발송
                    ring_placeholder.markdown("""
                    <div style="text-align: center; padding: 20px;">
                        <div style="font-size: 4rem;">📤</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: #667eea; margin-top: 10px;">
                            문자 발송 중...
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # SMS 발송
                    try:
                        from sms_manager import send_sms
                        success, result_msg = send_sms(clean_phone, sms_message)
                        
                        if success:
                            ring_placeholder.markdown(f"""
                            <div style="text-align: center; padding: 30px; 
                                        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                                        border-radius: 20px; color: white;">
                                <div style="font-size: 4rem;">✅</div>
                                <div style="font-size: 1.5rem; font-weight: bold; margin-top: 10px;">
                                    주문 링크 발송 완료!
                                </div>
                                <div style="font-size: 1rem; opacity: 0.9; margin-top: 8px;">
                                    📱 {clean_phone[:3]}-****-{clean_phone[-4:]}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            st.balloons()
                        else:
                            ring_placeholder.empty()
                            st.error(f"❌ 문자 발송 실패: {result_msg}")
                            st.info("💡 SMS API 설정을 확인해주세요. (secrets.toml)")
                            
                    except Exception as e:
                        ring_placeholder.empty()
                        st.error(f"❌ 오류 발생: {e}")
                        st.info("💡 SMS API 설정이 필요합니다.")
                    
                    progress_bar.empty()
            
            # 즉시 발송 버튼 (신호 없이)
            st.markdown("---")
            if st.button("💬 신호 없이 바로 발송", key="btn_instant_send", use_container_width=True):
                if not customer_phone_for_link:
                    st.error("❌ 손님 전화번호를 입력해주세요!")
                else:
                    clean_phone = customer_phone_for_link.replace("-", "").replace(" ", "")
                    
                    with st.spinner("문자 발송 중..."):
                        try:
                            from sms_manager import send_sms
                            success, result_msg = send_sms(clean_phone, sms_message)
                            
                            if success:
                                st.success(f"✅ 주문 링크가 {clean_phone[:3]}-****-{clean_phone[-4:]}로 발송되었습니다!")
                            else:
                                st.error(f"❌ 발송 실패: {result_msg}")
                        except Exception as e:
                            st.error(f"❌ 오류: {e}")
        
    except Exception as e:
        st.warning(f"⚠️ 주문 링크 생성 중 오류: {e}")

    st.markdown("---")

    # 탭 구성 - 가맹점용
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📦 주문 현황",
        "💳 가맹비 결제 관리",
        "🖨️ 프린터 설정",
        "📝 메뉴 수정",
        "🔗 QR코드 생성",
        "🚚 로젠택배 연동"
    ])

    # ==========================================
    # 📦 탭1: 실시간 주문 내역 (배민/요기요/쿠팡이츠 스타일)
    # ==========================================
    with tab1:
        # 자동 새로고침 설정
        col_title, col_refresh = st.columns([3, 1])
        with col_title:
            st.markdown("### 🔥 실시간 주문 현황")
        with col_refresh:
            auto_refresh = st.checkbox(
    "🔄 자동 새로고침", value=False, key="auto_refresh")
            if auto_refresh:
                st.markdown(
    '<div class="auto-refresh-badge"><span class="dot"></span>실시간 업데이트 중</div>',
    unsafe_allow_html=True)
                import time
                time.sleep(0.1)  # 부드러운 UI

        # 자동 새로고침 (30초마다)
        if auto_refresh:
            st.empty()
            import streamlit.components.v1 as components
            components.html(
                """<script>setTimeout(function(){window.parent.location.reload();}, 30000);</script>""",
                height=0
            )

        try:
            orders = get_orders_by_store(store_id)
        except Exception as e:
            st.error(f"❌ 주문 조회 실패: {e}")
            orders = []

        # 최신순 정렬
        orders_sorted = sorted(orders, key=lambda x: x.get(
            'order_time', ''), reverse=True) if orders else []

        # ==========================================
        # 📊 대시보드 통계 카드 (배민 스타일)
        # ==========================================
        pending_orders = [o for o in orders if o.get('status') == '접수대기']
        cooking_orders = [o for o in orders if o.get('status') == '조리중']
        delivering_orders = [o for o in orders if o.get('status') == '배달중']
        completed_orders = [o for o in orders if o.get('status') == '완료']

        # 오늘 매출 계산
        today = datetime.now().strftime("%Y-%m-%d")
        today_orders = [
    o for o in completed_orders if today in o.get(
        'order_time', '')]
        today_revenue = sum([int(o.get('total_price', 0) or 0)
                            for o in today_orders])

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div class="stats-card urgent">
                <div class="icon">🔔</div>
                <div class="value">{len(pending_orders)}</div>
                <div class="label">신규 주문</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="stats-card cooking">
                <div class="icon">🍳</div>
                <div class="value">{len(cooking_orders)}</div>
                <div class="label">조리 중</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="stats-card">
                <div class="icon">🚴</div>
                <div class="value">{len(delivering_orders)}</div>
                <div class="label">배달 중</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="stats-card revenue">
                <div class="icon">💰</div>
                <div class="value">{today_revenue:,}</div>
                <div class="label">오늘 매출(원)</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ==========================================
        # 🔍 상태별 필터 (요기요 스타일)
        # ==========================================
        if "order_filter" not in st.session_state:
            st.session_state.order_filter = "전체"

        filter_cols = st.columns(6)
        filter_options = [
            ("전체", len(orders), "all"),
            ("접수대기", len(pending_orders), "waiting"),
            ("조리중", len(cooking_orders), "cooking"),
            ("배달중", len(delivering_orders), "delivering"),
            ("완료", len(completed_orders), "completed"),
        ]

        for idx, (label, count, style) in enumerate(filter_options):
            with filter_cols[idx]:
                btn_type = "primary" if st.session_state.order_filter == label else "secondary"
                if st.button(f"{label} ({count})", key=f"filter_{label}",
                            use_container_width=True, type=btn_type):
                    st.session_state.order_filter = label
                    st.rerun()

        st.markdown("---")

        # 필터 적용
        if st.session_state.order_filter != "전체":
            filtered_orders = [o for o in orders_sorted if o.get(
                'status') == st.session_state.order_filter]
        else:
            filtered_orders = orders_sorted

        # ==========================================
        # 📦 주문 카드 리스트 (쿠팡이츠 스타일)
        # ==========================================
        if filtered_orders:
            for order in filtered_orders[:30]:  # 최근 30건
                order_id = order.get('order_id', 'N/A')
                status = order.get('status', '접수대기')
                order_time = order.get('order_time', '')
                order_content = order.get('order_content', '')
                customer_phone = order.get('customer_phone', '')
                address = order.get('address', '')
                total_price = order.get('total_price', '0')
                request_msg = order.get('request', '')

                # 경과 시간 계산
                elapsed_text = ""
                elapsed_class = ""
                try:
                    if order_time:
                        order_dt = datetime.strptime(
                            order_time, "%Y-%m-%d %H:%M:%S")
                        elapsed_mins = int(
    (datetime.now() - order_dt).total_seconds() / 60)
                        if elapsed_mins < 60:
                            elapsed_text = f"⏱️ {elapsed_mins}분 전"
                            if elapsed_mins > 30:
                                elapsed_class = "danger"
                            elif elapsed_mins > 15:
                                elapsed_class = "warning"
                        else:
                            elapsed_text = f"⏱️ {elapsed_mins // 60}시간 전"
                except:
                    elapsed_text = ""

                # 상태별 스타일 결정
                status_class = {
                    "접수대기": "waiting",
                    "조리중": "cooking",
                    "배달중": "delivering",
                    "완료": "completed",
                    "취소": "cancelled"
                }.get(status, "waiting")

                status_icon = {
                    "접수대기": "🔔 신규주문",
                    "조리중": "🍳 조리중",
                    "배달중": "🚴 배달중",
                    "완료": "✅ 완료",
                    "취소": "❌ 취소"
                }.get(status, "🔔 신규주문")

                # 신규 주문 강조
                new_order_class = "new-order" if status == "접수대기" else ""

                # 주문 카드 렌더링
                st.markdown(f"""
                <div class="order-card {new_order_class}">
                    <div class="order-header {status_class}">
                        <span class="order-status-badge">{status_icon}</span>
                        <span class="order-time-badge">{elapsed_text}</span>
                    </div>
                    <div class="order-body">
                        #{order_id} · {order_time}</div>
                        <div class="order-id">주문번호
                        <div class="order-content">📋 {order_content}</div>
                        <div class="order-info-row">
                            <span class="icon">📍</span>
                            <span>{address if address else '주소 미입력'}</span>
                        </div>
                        <div class="order-info-row">
                            <span class="icon">📞</span>
                            <span>{customer_phone if customer_phone else '연락처 미입력'}</span>
                        </div>
                        {"<div class='order-info-row'><span class='icon'>💬</span><span>" +
                            request_msg + "</span></div>" if request_msg else ""}
                        <div class="order-price">{int(total_price) if total_price else 0:,}<span>원</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 빠른 액션 버튼 (Streamlit 버튼)
                btn_cols = st.columns(4)

                with btn_cols[0]:
                    # 다음 상태로 전환
                    next_status_map = {
                        "접수대기": ("✅ 주문접수", "조리중"),
                        "조리중": ("🚴 배달시작", "배달중"),
                        "배달중": ("✅ 배달완료", "완료"),
                        "완료": (None, None),
                        "취소": (None, None)
                    }
                    next_label, next_status = next_status_map.get(
                        status, (None, None))

                    if next_label and next_status:
                        if st.button(
                            next_label, key=f"next_{order_id}", use_container_width=True, type="primary"):
                            if update_order_status(order_id, next_status):
                                st.success(f"✅ {next_status}(으)로 변경!")
                                st.rerun()

                with btn_cols[1]:
                    if status not in ["완료", "취소"]:
                        if st.button(
                            "❌ 취소", key=f"cancel_{order_id}", use_container_width=True):
                            if update_order_status(order_id, "취소"):
                                st.warning("주문이 취소되었습니다.")
                                st.rerun()

                with btn_cols[2]:
                    if customer_phone:
                        st.button(
    f"📞 전화",
    key=f"call_{order_id}",
    use_container_width=True)

                with btn_cols[3]:
                    # 상세 보기 (펼침)
                    with st.expander("📝 상세"):
                        st.markdown(f"""
                        **주문번호:** {order_id}
                        **주문시간:** {order_time}
                        **현재상태:** {status}
                        **주문내용:** {order_content}
                        **배달주소:** {address}
                        **연락처:** {customer_phone}
                        **금액:** {total_price}원
                        **요청사항:** {request_msg if request_msg else '없음'}
                        """)

                        # 상태 직접 선택
                        new_status = st.selectbox(
                            "상태 변경",
                            ["접수대기", "조리중", "배달중", "완료", "취소"],
                            index=["접수대기", "조리중", "배달중", "완료", "취소"].index(status),
                            key=f"select_{order_id}"
                        )
                        if st.button("변경 적용", key=f"apply_{order_id}"):
                            if update_order_status(order_id, new_status):
                                st.success("✅ 상태 변경 완료!")
                                st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)

        else:
            # 주문 없을 때
            st.markdown("""
            <div style="text-align: center; padding: 60px 20px; color: #999;">
                <div style="font-size: 4rem; margin-bottom: 20px;">📭</div>
                <div style="font-size: 1.3rem; font-weight: 600; margin-bottom: 10px;">주문이 없습니다</div>
                <div style="font-size: 0.95rem;">새 주문이 들어오면 여기에 표시됩니다</div>
            </div>
            """, unsafe_allow_html=True)

        # ==========================================
        # 🔔 알림 사운드 옵션
        # ==========================================
        st.markdown("---")
        with st.expander("🔔 알림 설정"):
            sound_enabled = st.checkbox(
    "새 주문 알림 소리", value=False, key="sound_alert")
            if sound_enabled and len(pending_orders) > 0:
                # 알림 소리 (브라우저 API 사용)
                import streamlit.components.v1 as components
                components.html("""
                <script>
                    // 알림 권한 요청 및 소리 재생
                    if (Notification.permission === 'default') {
                        Notification.requestPermission();
                    }
                    // 간단한 비프음
                    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    const oscillator = audioCtx.createOscillator();
                    oscillator.type = 'sine';
                    oscillator.frequency.setValueAtTime(
                        800, audioCtx.currentTime);
                    oscillator.connect(audioCtx.destination);
                    oscillator.start();
                    oscillator.stop(audioCtx.currentTime + 0.3);
                </script>
                """, height=0)

    # ==========================================
    # 💳 탭2: 가맹비 결제 관리
    # ==========================================
    with tab2:
        st.markdown("### 💳 가맹비 결제 관리")
        st.markdown("서비스 이용을 위한 가맹비 결제를 관리합니다.")

        # 현재 결제 상태 다시 가져오기
        current_billing_key = store_info.get('billing_key', '')
        current_expiry = store_info.get('expiry_date', '')
        current_payment_status = store_info.get('payment_status', '미등록')
        current_next_payment = store_info.get('next_payment_date', '')

        st.markdown("---")

        # ==========================================
        # 📊 현재 서비스 상태 (큰 카드)
        # ==========================================
        # 남은 일수 계산
        days_left = 0
        if current_expiry:
            try:
                exp_date = datetime.strptime(current_expiry, "%Y-%m-%d")
                days_left = (exp_date.date() - datetime.now().date()).days
            except:
                days_left = 0

        # 무료 체험 중인지 확인
        is_free_trial = current_payment_status == '무료체험'

        if current_expiry:
            if is_expired(current_expiry):
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
                            padding: 2rem; border-radius: 20px; text-align: center; color: white; margin-bottom: 1rem;">
                    <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">⚠️ 서비스가 만료되었습니다</div>
                    <div style="font-size: 2.5rem; font-weight: bold;">만료일: {current_expiry}</div>
                    <div style="font-size: 1rem; margin-top: 0.5rem; opacity: 0.9;">결제를 완료하시면 서비스가 재개됩니다.</div>
                </div>
                """, unsafe_allow_html=True)
            elif is_free_trial:
                # 무료 체험 중
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                            padding: 2rem; border-radius: 20px; text-align: center; color: white; margin-bottom: 1rem;">
                    <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">🎁 무료 체험 중</div>
                    <div style="font-size: 2.5rem; font-weight: bold;">{days_left}일 남음</div>
                    <div style="font-size: 1rem; margin-top: 0.5rem; opacity: 0.9;">만료일: {current_expiry}</div>
                </div>
                """, unsafe_allow_html=True)

                # 무료 체험 종료 후 선택 안내
                st.markdown("---")
                st.markdown("### 🎯 무료 체험 종료 후 선택")
                st.markdown("무료 체험 기간이 끝나면 아래 중 하나를 선택해주세요.")

                col_choice1, col_choice2 = st.columns(2)

                with col_choice1:
                    st.markdown("""
                    <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                                padding: 1.5rem; border-radius: 15px; color: white; text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: bold;">✅ 정기 결제 신청</div>
                        <div style="font-size: 0.9rem; margin-top: 0.5rem;">카드를 등록하면 자동 결제되어<br>서비스가 계속됩니다.</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("")

                with col_choice2:
                    st.markdown("""
                    <div style="background: linear-gradient(135deg, #bdc3c7 0%, #2c3e50 100%);
                                padding: 1.5rem; border-radius: 15px; color: white; text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: bold;">❌ 서비스 해지</div>
                        <div style="font-size: 0.9rem; margin-top: 0.5rem;">무료 체험만 사용하고<br>서비스를 종료합니다.</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(
                        "🚫 서비스 해지 신청", use_container_width=True, key="cancel_service"):
                        # 해지 확인
                        st.session_state.show_cancel_confirm = True

                # 해지 확인 대화상자
                if st.session_state.get('show_cancel_confirm', False):
                    st.warning("⚠️ 정말로 서비스를 해지하시겠습니까?")
                    col_confirm1, col_confirm2 = st.columns(2)
                    with col_confirm1:
                        if st.button(
                            "✅ 예, 해지합니다", use_container_width=True, type="primary"):
                            # 만료일을 오늘로 설정하여 서비스 종료
                            today = datetime.now().strftime("%Y-%m-%d")
                            if update_billing_info(
                                store_id, '', today, '해지', ''):
                                st.success("서비스가 해지되었습니다. 이용해주셔서 감사합니다.")
                                st.session_state.show_cancel_confirm = False
                                st.rerun()
                    with col_confirm2:
                        if st.button("❌ 아니오, 취소", use_container_width=True):
                            st.session_state.show_cancel_confirm = False
                            st.rerun()
            else:
                # 정상 이용 중
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                            padding: 2rem; border-radius: 20px; text-align: center; color: white; margin-bottom: 1rem;">
                    <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">✅ 서비스 이용 중</div>
                    <div style="font-size: 2.5rem; font-weight: bold;">만료일: {current_expiry}</div>
                    <div style="font-size: 1.2rem; margin-top: 0.5rem;">({days_left}일 남음)</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        padding: 2rem; border-radius: 20px; text-align: center; color: white; margin-bottom: 1rem;">
                <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">📋 결제 정보 미등록</div>
                <div style="font-size: 1.8rem; font-weight: bold;">신용카드를 등록하시면 자동 결제됩니다</div>
                <div style="font-size: 1rem; margin-top: 0.5rem; opacity: 0.9;">또는 무통장 입금으로 결제 가능합니다.</div>
            </div>
            """, unsafe_allow_html=True)

        # 결제 상태 상세
        col1, col2 = st.columns(2)
        with col1:
            if current_payment_status == '정상':
                st.success(f"✅ 결제 상태: **{current_payment_status}**")
            elif current_payment_status == '실패':
                st.error(
    f"❌ 결제 상태: **{current_payment_status}** - 카드 정보를 확인해주세요")
            else:
                st.warning(f"⚠️ 결제 상태: **{current_payment_status}**")

        with col2:
            if current_next_payment:
                st.info(f"📅 다음 자동결제일: **{current_next_payment}**")
            else:
                st.info("📅 다음 자동결제일: 미설정")

        st.markdown("---")

        # ==========================================
        # = :::::::::::::::::::::::::::::::::::::: =
        # 💳 새 결제수단 등록 섹션
        # = :::::::::::::::::::::::::::::::::::::: =
        st.markdown("---")
        st.markdown("### ➕ 새 결제수단 등록")
        
        if "reg_step" not in st.session_state:
            st.session_state.reg_step = "select" # select -> account_detail

        # ------------------------------------------
        # [STEP 1] 결제 수단 선택 (카드 공사중 반영)
        # ------------------------------------------
        if st.session_state.reg_step == "select":
            with st.container(border=True):
                st.markdown("#### 💳 1단계: 결제 수단 선택")
                st.caption("등록하실 결제 수단을 선택해 주세요.")
                
                col_sel1, col_sel2 = st.columns(2)
                
                with col_sel1:
                    st.markdown("""
                    <div style="padding: 20px; border: 2px solid #000; border-radius: 15px; text-align: center;">
                        <div style="font-size: 2rem;">🏦</div>
                        <div style="font-weight: bold; margin-top: 10px;">계좌 결제</div>
                        <div style="font-size: 0.8rem; color: #666;">자동 이체 등록</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("계좌 등록하기", use_container_width=True):
                        st.session_state.reg_step = "account_detail"
                        st.rerun()
                
                with col_sel2:
                    st.markdown("""
                    <div style="padding: 20px; border: 2px solid #ddd; border-radius: 15px; text-align: center; background-color: #f9f9f9; position: relative;">
                        <div style="position: absolute; top: 10px; right: 10px; background: #ff4b4b; color: white; padding: 2px 8px; border-radius: 5px; font-size: 0.7rem;">공사중</div>
                        <div style="font-size: 2rem; opacity: 0.5;">💳</div>
                        <div style="font-weight: bold; margin-top: 10px; color: #aaa;">신용카드</div>
                        <div style="font-size: 0.8rem; color: #aaa;">정기 결제 등록</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.button("카드 등록 (준비중)", use_container_width=True, disabled=True)

        # ------------------------------------------
        # [STEP 2] 계좌 상세 정보 입력
        # ------------------------------------------
        elif st.session_state.reg_step == "account_detail":
            with st.container(border=True):
                st.markdown("#### 🏦 2단계: 계좌 정보 입력")
                
                acc_holder = st.text_input("예금주 성함", placeholder="실명 입력")
                bank_name = st.selectbox("은행 선택", ["국민은행", "신한은행", "우리은행", "하나은행", "카카오뱅크", "토스뱅크"])
                acc_num = st.text_input("계좌번호", placeholder="'-' 제외 입력")
                st.caption("※ 매월 정기적으로 이용료가 자동 인출됩니다.")
                
                if st.button("💾 계좌 등록 완료", use_container_width=True, type="primary"):
                    if acc_holder and acc_num:
                        with st.spinner("금융기관에 계좌를 등록 중입니다..."):
                            import time
                            time.sleep(2)
                            st.session_state.reg_step = "select" # 초기화
                            st.success(f"🎉 {acc_holder} 사장님의 계좌가 성공적으로 등록되었습니다!")
                            st.balloons()
                    else:
                        st.error("❌ 모든 정보를 입력해 주세요.")
                
                if st.button("⬅️ 뒤로가기", key="back_to_select"):
                    st.session_state.reg_step = "select"
                    st.rerun()

        st.markdown("---")
        
        # 💳 결제 방법 선택
        # ==========================================
        st.markdown("### 결제 방법 선택")

        payment_method = st.radio(
            "결제 방법",
            ["💳 신용카드 정기 결제", "🏦 무통장 입금"],
            horizontal=True,
            label_visibility="collapsed"
        )

        if "신용카드" in payment_method:
            # ==========================================
            # 💳 신용카드 정기 결제 등록
            # ==========================================
            st.markdown("### 💳 신용카드 정기 결제")
            st.markdown("신용카드를 등록하시면 매월 자동으로 결제됩니다.")

            # API 키 확인
            secret_key, client_key = get_toss_credentials()

            if not secret_key or not client_key:
                st.warning("⚠️ 토스페이먼츠 API 키가 설정되지 않았습니다.")
                st.info("관리자에게 문의하여 결제 시스템 설정을 요청해주세요.")
            else:
                # 현재 카드 등록 상태
                if current_billing_key:
                    st.markdown("""
                    <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                                padding: 1.5rem; border-radius: 15px; color: white; margin-bottom: 1rem;">
                        <div style="font-size: 1.2rem; font-weight: bold;">✅ 카드가 등록되어 있습니다</div>
                        <div style="font-size: 0.9rem; margin-top: 0.5rem; opacity: 0.9;">매월 자동으로 결제가 진행됩니다.</div>
                    </div>
                    """, unsafe_allow_html=True)

                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("🔄 다른 카드로 변경하기",
                                    use_container_width=True, type="primary"):
                            st.session_state.show_card_form = True
                    with col_btn2:
                        if st.button("🗑️ 카드 등록 해제", use_container_width=True):
                            # 빌링키 삭제
                            if update_billing_info(
                                store_id, '', '', '미등록', ''):
                                st.success("카드 등록이 해제되었습니다.")
                                st.rerun()
                else:
                    st.markdown("""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                padding: 1.5rem; border-radius: 15px; color: white; margin-bottom: 1rem;">
                        <div style="font-size: 1.2rem; font-weight: bold;">💳 신용카드를 등록해주세요</div>
                        <div style="font-size: 0.9rem; margin-top: 0.5rem; opacity: 0.9;">카드를 등록하면 편리하게 자동 결제됩니다.</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.session_state.show_card_form = True

                # 카드 등록 폼
                if st.session_state.get(
                    'show_card_form', not current_billing_key):
                    st.markdown("---")
                    st.markdown("**카드 정보 입력**")
                    st.caption("🔒 카드 정보는 토스페이먼츠에서 안전하게 처리됩니다.")

                    with st.form("card_registration"):
                        col1, col2 = st.columns(2)

                        with col1:
                            card_number = st.text_input(
                                "카드번호 (16자리)",
                                placeholder="1234-5678-9012-3456",
                                max_chars=19
                            )
                            expiry_month = st.text_input(
                                "유효기간 (월)",
                                placeholder="MM",
                                max_chars=2
                            )
                            card_password = st.text_input(
                                "카드 비밀번호 앞 2자리",
                                type="password",
                                placeholder="**",
                                max_chars=2
                            )

                        with col2:
                            id_number = st.text_input(
                                "생년월일 6자리 (또는 사업자번호)",
                                placeholder="YYMMDD",
                                max_chars=10
                            )
                            expiry_year = st.text_input(
                                "유효기간 (년)",
                                placeholder="YY",
                                max_chars=2
                            )

                        st.markdown("---")
                        st.markdown(
                            f"**월 이용료: {get_bank_transfer_info()['monthly_fee']:,}원**")

                        submitted = st.form_submit_button(
    "💳 카드 등록 및 결제", use_container_width=True, type="primary")

                        if submitted:
                            if not all([card_number, expiry_month,
                                        expiry_year, card_password, id_number]):
                                st.error("❌ 모든 정보를 입력해주세요.")
                            else:
                                with st.spinner("카드 등록 중..."):
                                    result, error = issue_billing_key_with_card(
                                        customer_key=store_id,
                                        card_number=card_number,
                                        expiry_year=expiry_year,
                                        expiry_month=expiry_month,
                                        card_password=card_password,
                                        id_number=id_number
                                    )

                                if error:
                                    st.error(f"❌ 카드 등록 실패: {error}")
                                else:
                                    billing_key = result['billing_key']

                                    # 첫 결제 실행
                                    with st.spinner("첫 결제 진행 중..."):
                                        order_id = generate_order_id(store_id)
                                        payment_result, pay_error = execute_billing_payment(
                                            billing_key=billing_key,
                                            customer_key=store_id,
                                            amount=get_bank_transfer_info()[
                                                                            'monthly_fee'],
                                            order_id=order_id,
                                            order_name="AI스토어 월 이용료"
                                        )

                                    if pay_error:
                                        st.error(f"❌ 결제 실패: {pay_error}")
                                    else:
                                        # 결제 성공 - DB 업데이트
                                        new_expiry = calculate_expiry_date(30)
                                        new_next_payment = calculate_next_payment_date(
                                            30)

                                        update_billing_info(
                                            store_id=store_id,
                                            billing_key=billing_key,
                                            expiry_date=new_expiry,
                                            payment_status='정상',
                                            next_payment_date=new_next_payment
                                        )

                                        # 세션 업데이트
                                        store_info['billing_key'] = billing_key
                                        store_info['expiry_date'] = new_expiry
                                        store_info['payment_status'] = '정상'
                                        store_info['next_payment_date'] = new_next_payment
                                        st.session_state.store_info = store_info

                                        st.success("✅ 카드 등록 및 결제 완료!")
                                        st.info(
    f"결제 금액: {
        payment_result['amount']:,}원")
                                        st.info(f"만료일: {new_expiry}")
                                        st.balloons()
                                        st.rerun()

        else:
            # ==========================================
            # 🏦 무통장 입금 안내
            # ==========================================
            st.markdown("### 🏦 무통장 입금 안내")

            bank_info = get_bank_transfer_info()

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; padding: 25px; border-radius: 15px; margin: 15px 0;">
                <h3 style="margin: 0 0 15px 0;">💰 입금 계좌 정보</h3>
                <p style="font-size: 1.3rem; margin: 8px 0;"><strong>은행:</strong> {bank_info['bank_name']}</p>
                <p style="font-size: 1.3rem; margin: 8px 0;"><strong>계좌번호:</strong> {bank_info['account_number']}</p>
                <p style="font-size: 1.3rem; margin: 8px 0;"><strong>예금주:</strong> {bank_info['account_holder']}</p>
                <hr style="border-color: rgba(255,255,255,0.3); margin: 15px 0;">
                <p style="font-size: 1.5rem; margin: 8px 0;"><strong>월 이용료:</strong> {bank_info['monthly_fee']:,}원</p>
            </div>
            """, unsafe_allow_html=True)

            st.warning(f"⚠️ **{bank_info['note']}**")

            st.markdown("---")
            st.markdown("**입금 확인 안내**")
            st.info("""
            1. 위 계좌로 월 이용료를 입금해주세요.
            2. 입금자명에 **가게명**을 기재해주세요.
            3. 입금 확인 후 **1영업일 이내**에 서비스가 활성화됩니다.
            4. 문의사항은 관리자에게 연락해주세요.
            """)

            # 입금 완료 신고
            st.markdown("---")
            st.markdown("**입금 완료 신고**")

            col1, col2 = st.columns(2)
            with col1:
                deposit_name = st.text_input("입금자명", placeholder="홍길동")
            with col2:
                deposit_date = st.date_input("입금일자")

            if st.button("📤 입금 완료 신고", use_container_width=True,
                        type="primary"):
                if deposit_name:
                    st.success("✅ 입금 완료 신고가 접수되었습니다.")
                    st.info("관리자 확인 후 서비스가 활성화됩니다.")
                else:
                    st.error("❌ 입금자명을 입력해주세요.")

    # ==========================================
    # 🖨️ 탭3: 프린터 설정
    # ==========================================
    with tab3:
        st.markdown("### 🖨️ POS 프린터 설정")

        # 라이브러리 상태 확인
        if ESCPOS_AVAILABLE:
            st.success("✅ 프린터 라이브러리 설치됨 (python-escpos)")
        else:
            st.warning("⚠️ python-escpos 라이브러리가 설치되지 않았습니다.")
            st.code("pip install python-escpos", language="bash")

        st.markdown("---")
        
        # 프린터 연결 유형 선택
        printer_type = st.radio(
            "📶 프린터 연결 방식",
            ["📱 블루투스 (핸드폰)", "🌐 Wi-Fi (네트워크)"],
            horizontal=True
        )
        
        st.markdown("---")
        
        # ==========================================
        # 📱 블루투스 프린터 설정
        # ==========================================
        if "블루투스" in printer_type:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 1.5rem; border-radius: 15px; color: white; margin-bottom: 1rem;">
                <h3 style="margin: 0 0 0.5rem 0; color: white;">📱 블루투스 프린터 연결</h3>
                <p style="margin: 0; opacity: 0.9; font-size: 0.95rem;">
                    핸드폰 블루투스로 휴대용 프린터를 직접 연결합니다.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # 블루투스 연결 JavaScript
            from printer_manager import get_bluetooth_printer_js
            st.components.v1.html(get_bluetooth_printer_js() + """
            <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 1rem;">
                <button onclick="connectBluetoothPrinter()" 
                        style="background: #4CAF50; color: white; border: none; 
                               padding: 15px 30px; border-radius: 25px; cursor: pointer;
                               font-weight: bold; font-size: 1.1rem; flex: 1;">
                    🔗 블루투스 프린터 연결
                </button>
                <button onclick="disconnectBluetoothPrinter()" 
                        style="background: #f44336; color: white; border: none; 
                               padding: 15px 30px; border-radius: 25px; cursor: pointer;
                               font-weight: bold; font-size: 1.1rem;">
                    ❌ 해제
                </button>
            </div>
            
            <div style="background: #e8f5e9; padding: 1rem; border-radius: 10px; margin-top: 1rem;">
                <strong>📋 연결 방법:</strong>
                <ol style="margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
                    <li>블루투스 프린터 전원 켜기</li>
                    <li>핸드폰 블루투스 활성화</li>
                    <li>위 [🔗 블루투스 프린터 연결] 버튼 클릭</li>
                    <li>프린터 선택 후 연결 완료!</li>
                </ol>
            </div>
            """, height=280)
            
            # 지원 프린터 목록
            with st.expander("📋 지원 블루투스 프린터 목록"):
                st.markdown("""
                | 브랜드 | 모델 | 용지 |
                |-------|------|-----|
                | **Epson** | TM-P20, TM-P60, TM-P80 | 58mm, 80mm |
                | **Star Micronics** | SM-S210i, SM-L200 | 58mm |
                | **Bixolon** | SPP-R200III, SPP-R310 | 58mm, 80mm |
                | **XPrinter** | P323B, XP-P300 | 58mm, 80mm |
                | **GOOJPRT** | PT-210, MTP-II | 58mm |
                | **MUNBYN** | IMP001, IMP002 | 58mm, 80mm |
                """)
            
            # 블루투스 설정 가이드
            with st.expander("❓ 블루투스 연결이 안될 때"):
                st.markdown("""
                ### 🔧 문제 해결
                
                **1. 프린터가 목록에 없어요**
                - 프린터 전원을 껐다가 다시 켜세요
                - 핸드폰 블루투스를 껐다가 켜세요
                - 프린터가 다른 기기에 연결되어 있으면 해제하세요
                
                **2. 연결은 됐는데 출력이 안돼요**
                - 프린터 용지가 있는지 확인하세요
                - 프린터 배터리를 확인하세요
                - 프린터를 재시작하세요
                
                **3. 브라우저 호환성**
                - ✅ Chrome, Edge, Opera 지원
                - ❌ Safari, Firefox 미지원
                - HTTPS 환경 필요 (localhost 제외)
                """)
        
        # ==========================================
        # 🌐 Wi-Fi 프린터 설정
        # ==========================================
        else:
            st.markdown("""
            **Wi-Fi 프린터 연결 방법:**
            1. 프린터를 같은 Wi-Fi 네트워크에 연결
            2. 프린터 설정에서 IP 주소 확인 (보통 192.168.x.x)
            3. 아래에 IP 주소 입력 후 테스트
            """)

            st.markdown("---")

            current_ip = store_info.get('printer_ip', '') if store_info else ''

            col1, col2 = st.columns(2)

            with col1:
                new_ip = st.text_input(
                    "프린터 IP 주소",
                    value=current_ip,
                    placeholder="192.168.0.100"
                )

                new_port = st.text_input(
                    "포트 번호",
                    value="9100",
                    help="기본값: 9100"
                )

            with col2:
                st.markdown("<br>", unsafe_allow_html=True)

                # 테스트 버튼
                if st.button("🔌 연결 테스트", use_container_width=True):
                    if new_ip:
                        with st.spinner("프린터 연결 중..."):
                            success, msg = test_printer_connection(
                                new_ip, int(new_port or 9100))

                        if success:
                            st.success(f"✅ {msg}")
                        else:
                            st.error(f"❌ {msg}")
                    else:
                        st.warning("IP 주소를 입력해주세요.")

            # 저장 버튼
            if st.button("💾 설정 저장", use_container_width=True):
                store_info['printer_ip'] = new_ip
                if save_store(store_id, store_info):
                    st.session_state.store_info = store_info  # 세션 업데이트
                    st.success("✅ 프린터 설정 저장 완료!")
                else:
                    st.error("❌ 저장 실패")

    # ==========================================
    # 📝 탭4: 메뉴 수정
    # ==========================================
    with tab4:
        st.markdown("### 📝 우리 가게 메뉴 수정")
        st.markdown("---")

        current_menu = store_info.get('menu_text', '')

        st.markdown("**현재 메뉴:**")
        if current_menu:
            st.text(current_menu)
        else:
            st.info("등록된 메뉴가 없습니다.")

        st.markdown("---")

        new_menu = st.text_area(
            "메뉴 내용 수정",
            value=current_menu,
            height=300,
            placeholder="메뉴명 - 가격\n예: 후라이드치킨 - 18000원"
        )

        col1, col2 = st.columns(2)

        with col1:
            new_info = st.text_area(
                "영업정보 수정",
                value=store_info.get('info', ''),
                placeholder="영업시간: 11:00 ~ 22:00\n휴무일: 매주 월요일"
            )

        with col2:
            new_phone = st.text_input(
                "연락처 수정",
                value=store_info.get('phone', '')
            )

            if st.button("💾 메뉴/정보 저장", use_container_width=True, type="primary"):
                store_info['menu_text'] = new_menu
                store_info['info'] = new_info
                store_info['phone'] = new_phone

                if save_store(store_id, store_info):
                    st.session_state.store_info = store_info  # 세션 업데이트
                    st.success("✅ 메뉴 및 정보 저장 완료!")
                else:
                    st.error("❌ 저장 실패")
        
        # ==========================================
        # 🪑 테이블 설정 (식당/카페인 경우)
        # ==========================================
        st.markdown("---")
        st.markdown("### 🪑 테이블 설정")
        st.info("테이블 정보를 설정하면 고객 예약 시 자동으로 가용 테이블을 확인합니다.")
        
        col_table1, col_table2 = st.columns(2)
        
        with col_table1:
            current_table_count = int(store_info.get('table_count', 0) or 0)
            new_table_count = st.number_input(
                "테이블 수",
                min_value=0,
                max_value=100,
                value=current_table_count,
                help="매장 내 총 테이블 수"
            )
        
        with col_table2:
            current_seats = int(store_info.get('seats_per_table', 0) or 0)
            new_seats_per_table = st.number_input(
                "테이블당 최대 착석 인원",
                min_value=0,
                max_value=20,
                value=current_seats,
                help="한 테이블에 앉을 수 있는 최대 인원"
            )
        
        if new_table_count > 0 and new_seats_per_table > 0:
            total_capacity = new_table_count * new_seats_per_table
            st.success(f"📊 총 수용 가능 인원: **{total_capacity}명** ({new_table_count}테이블 × {new_seats_per_table}명)")
        
        if st.button("💾 테이블 설정 저장", use_container_width=True):
            store_info['table_count'] = new_table_count
            store_info['seats_per_table'] = new_seats_per_table
            
            if save_store(store_id, store_info):
                st.session_state.store_info = store_info
                st.success("✅ 테이블 설정이 저장되었습니다!")

# ==========================================
# 🔗 탭5: QR코드 생성
# ==========================================
    with tab5:
        st.markdown("### 🔗 우리 가게 QR코드 생성")
    st.markdown("---")

    st.markdown("고객이 스캔하면 주문 페이지로 바로 연결됩니다!")

    # QR코드 설정
    col1, col2 = st.columns(2)

    with col1:
        qr_base_url = st.text_input(
            "주문 페이지 URL",
            value="https://your-app.streamlit.app",
            help="Streamlit Cloud 배포 URL"
        )

        # 가게 ID를 URL에 자동 추가
        full_url = f"{qr_base_url}?store={store_id}"
        st.info(f"🔗 전체 URL: {full_url}")

    with col2:
        qr_size = st.slider("QR코드 크기", 5, 15, 10)

    if st.button("🔲 QR코드 생성", use_container_width=True):
        if qr_base_url:
            # QR코드 생성
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=qr_size,
                border=4
            )
            qr.add_data(full_url)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white")

            # 이미지를 바이트로 변환
            img_buffer = io.BytesIO()
            qr_img.save(img_buffer, format='PNG')
            img_buffer.seek(0)

            col1, col2 = st.columns([1, 2])

            with col1:
                st.image(img_buffer, caption=store_name, width=250)

            with col2:
                st.success("✅ QR코드 생성 완료!")
                st.markdown(f"**가게:** {store_name}")
                st.markdown(f"**연결 URL:** {full_url}")

                # 다운로드 버튼
                img_buffer.seek(0)
                st.download_button(
                    label="📥 QR코드 다운로드",
                    data=img_buffer,
                    file_name=f"qrcode_{store_id}.png",
                    mime="image/png"
                )
        else:
            st.warning("URL을 입력해주세요.")

    # ==========================================
    # 🚚 탭6: 로젠택배 연동 설정
    # ==========================================
    with tab6:
        st.markdown("### 🚚 로젠택배 계정 연동")
        
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 1.5rem;
            border-radius: 20px;
            margin-bottom: 1.5rem;
            color: white;
        ">
            <div style="font-size: 1.3rem; font-weight: 700; margin-bottom: 10px;">
                📦 로젠택배 사장님 계정 연동
            </div>
            <div style="font-size: 1rem; opacity: 0.95;">
                로젠택배 사이트 계정을 연동하면 택배 접수 시 자동으로 발송인 정보가 입력됩니다.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 현재 저장된 로젠택배 정보 가져오기
        current_logen_id = store_info.get('logen_id', '')
        current_logen_password = store_info.get('logen_password', '')
        current_sender_name = store_info.get('logen_sender_name', store_info.get('name', ''))
        current_sender_address = store_info.get('logen_sender_address', '')
        
        # 연동 상태 표시
        if current_logen_id:
            st.success(f"✅ 로젠택배 계정 연동됨: **{current_logen_id}**")
        else:
            st.warning("⚠️ 로젠택배 계정이 연동되지 않았습니다.")
        
        st.markdown("#### 📋 로젠택배 계정 정보")
        
        col_logen1, col_logen2 = st.columns(2)
        
        with col_logen1:
            new_logen_id = st.text_input(
                "🆔 로젠택배 아이디",
                value=current_logen_id,
                placeholder="로젠택배 사이트 로그인 ID",
                help="로젠택배 (ilogen.com) 로그인 아이디"
            )
        
        with col_logen2:
            new_logen_password = st.text_input(
                "🔐 로젠택배 비밀번호",
                value=current_logen_password,
                type="password",
                placeholder="로젠택배 사이트 비밀번호",
                help="비밀번호는 암호화되어 저장됩니다"
            )
        
        st.markdown("#### 📍 발송인 기본 정보")
        st.caption("택배 접수 시 자동으로 입력되는 발송인 정보입니다.")
        
        new_sender_name = st.text_input(
            "👤 발송인명",
            value=current_sender_name,
            placeholder="예: 동네비서 / 홍길동",
            help="택배 발송 시 표시되는 이름"
        )
        
        new_sender_address = st.text_area(
            "🏠 발송인 주소",
            value=current_sender_address,
            placeholder="예: 서울특별시 강남구 테헤란로 123, 동네비서빌딩 1층",
            help="택배 픽업 주소 (가게 주소)",
            height=100
        )
        
        new_sender_phone = st.text_input(
            "📞 발송인 연락처",
            value=store_info.get('phone', ''),
            placeholder="01012345678",
            help="택배 기사가 연락할 번호"
        )
        
        st.markdown("---")
        
        # 저장 버튼
        if st.button("💾 로젠택배 정보 저장", key="btn_save_logen", use_container_width=True, type="primary"):
            # 정보 업데이트
            store_info['logen_id'] = new_logen_id
            store_info['logen_password'] = new_logen_password
            store_info['logen_sender_name'] = new_sender_name
            store_info['logen_sender_address'] = new_sender_address
            if new_sender_phone:
                store_info['phone'] = new_sender_phone
            
            if save_store(store_id, store_info):
                st.session_state.store_info = store_info
                st.success("✅ 로젠택배 정보가 저장되었습니다!")
                st.balloons()
            else:
                st.error("❌ 저장 중 오류가 발생했습니다.")
        
        st.markdown("---")
        
        # 로젠택배 바로가기
        st.markdown("#### 🔗 로젠택배 바로가기")
        
        col_link1, col_link2 = st.columns(2)
        
        with col_link1:
            st.link_button(
                "🌐 로젠택배 사이트",
                "https://www.ilogen.com/",
                use_container_width=True
            )
        
        with col_link2:
            st.link_button(
                "📦 택배 접수하기",
                "https://www.ilogen.com/web/personal/tkSendOrder",
                use_container_width=True
            )
        
        st.caption("💡 로젠택배 회원가입이 필요한 경우 위 링크에서 가입하세요.")


# ==========================================
# 📌 푸터
# ==========================================
st.markdown("---")
with st.sidebar:
    st.markdown("---")
    with st.expander("📱 모바일 동시 확인 QR"):
        mobile_url = "https://dnbsir.com"
        qr = qrcode.make(mobile_url)
        buf = io.BytesIO()
        qr.save(buf)
        st.image(buf, width=150)
        st.caption("폰으로 스캔해서 확인하세요")

if st.session_state.user_type == "master":
    st.caption("👑 슈퍼 관리자 모드 | 전체 가맹점 관리 가능")
else:
    st.caption(f"🏪 {st.session_state.store_info.get('name', '')} 사장님 전용 페이지")
st.caption("📊 데이터: Google Sheets | 권한별 메뉴 분리 버전")
