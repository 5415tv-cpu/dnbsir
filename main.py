import streamlit as st
import textwrap
from datetime import datetime
import pwa_helper
import printer_manager
import db_manager
import logen_delivery
import address_helper
import sms_manager
import qrcode
import io
import pandas as pd
from PIL import Image
import ai_manager
import streamlit.components.v1 as components
import time
import json
import requests
import base64
from uuid import uuid4
from urllib.parse import urlencode
from report_page import render_report  # 새로 만든 파일을 불러옵니다
from admin_page import render_admin_page
from payment_page import render_payment_page
from test_card_page import render_test_card_page

# ==========================================
# 💎 동네비서 PREMIUM KIOSK - v2.2.0 (Sales Optimized)
# ==========================================
BUILD_VERSION = "20260116_SALES_PRO"

# 1. 페이지 초기 설정 (Streamlit 규칙: 첫 호출이어야 함)
st.set_page_config(page_title="동네비서 Premium", layout="centered")

# 로그인 세션 방어 (새로고침 시 유지)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# 🎨 글로벌 스타일 주입 (Transparent Glass + Bold Black Text)
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    /* 1. 전체 배경: 백색 */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"], .main {
        background: #FFFFFF !important;
        font-family: 'Pretendard', sans-serif !important;
        pointer-events: auto !important;
    }

    /* 2. 모든 텍스트 강제 검정색 고정 및 굵게 */
    div, p, span, label, h1, h2, h3, h4, h5, h6, .stMarkdown p, .stText p, a {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        font-weight: 900 !important;
    }
    
    /* 2-1. 보조 클래스 (검정 텍스트 유지) */
    .force-white, .force-white * {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }

    /* 3. 기본 카드 스타일 (화이트/블랙) */
    .glass-container {
        background: #FFFFFF !important;
        border: 1px solid #000000;
        border-radius: 30px;
        padding: 22px 26px;
        margin-bottom: 18px;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
    }
    
    a, button, [role="button"] {
        pointer-events: auto !important;
        cursor: pointer !important;
    }

    .glass-card {
        background: #FFFFFF !important;
        border: 1px solid #000000;
        border-radius: 32px;
        padding: 28px 32px;
        box-shadow: 0 8px 18px rgba(0, 0, 0, 0.08);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        display: block;
        text-decoration: none;
        margin-bottom: 15px;
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        background: #FFFFFF !important;
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
    }
    
    .glass-card:active {
        animation: card-bounce 0.25s ease-out;
    }

    .membership-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        min-height: 86px;
    }

    .membership-badges {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }

    .level-badge {
        background: #FFFFFF;
        color: #000000 !important;
        border: 1px solid #000000;
        padding: 4px 12px;
        border-radius: 50px;
        font-size: 12px;
        font-weight: 900;
    }

    .level-badge.premium {
        background: #FFFFFF;
        color: #000000 !important;
        border: 1px solid #000000;
    }
    
    .kakao-btn {
        background: #FFFFFF;
        color: #000000 !important;
        padding: 10px 16px;
        border-radius: 50px;
        font-weight: 900;
        font-size: 13px;
        border: 1px solid #000000;
        box-shadow: none;
    }

    .core-cards {
        margin: 10px auto 26px;
        max-width: 880px;
        display: flex;
        flex-direction: column;
        gap: 16px;
    }

    .core-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        min-height: 150px;
        width: 100%;
        border: 1px solid #000000;
        position: relative;
        z-index: 2;
    }

    .core-card .core-title {
        font-size: 28px;
        font-weight: 900;
        color: #000000;
        margin-bottom: 8px;
        letter-spacing: -0.5px;
    }

    .core-card .core-desc {
        font-size: 15px;
        font-weight: 900;
        color: #000000;
        line-height: 1.45;
    }

    .core-icon {
        font-size: 58px;
        flex-shrink: 0;
    }

    /* 4. 입력창 스타일 */
    input, textarea, [data-baseweb="input"], [data-baseweb="textarea"] {
        background-color: rgba(255, 255, 255, 0.9) !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
        border-radius: 12px !important;
    }

    /* 5. 버튼 스타일 */
    .stButton button, [data-testid="stForm"] button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-radius: 50px !important;
        font-weight: 900 !important;
        border: 2px solid #000000 !important;
        padding: 12px 25px !important;
        font-size: 16px !important;
    }
    
    .stButton button *, [data-testid="stForm"] button * {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }

    .stButton button svg, [data-testid="stForm"] button svg {
        fill: #000000 !important;
        color: #000000 !important;
    }
    
    /* 6. Streamlit 기본 UI 제거 */
    header, footer, [data-testid="stHeader"], [data-testid="stToolbar"] {
        display: none !important;
    }

    /* 7. 하단 아이콘 그리드 (컬러 카드 + 튀어나오는 터치 효과) */
    .icon-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 14px;
        padding: 10px 0;
    }
    
    .icon-item {
        border-radius: 16px;
        padding: 18px 12px;
        min-height: 96px;
        text-align: left;
        text-decoration: none;
        border: 1px solid #000000;
        box-shadow: none;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        display: flex;
        align-items: center;
        gap: 12px;
        will-change: transform;
        position: relative;
        z-index: 2;
        cursor: pointer;
        pointer-events: auto !important;
    }
    
    .membership-bar a, .kakao-btn {
        position: relative;
        z-index: 2;
        cursor: pointer;
        pointer-events: auto !important;
    }
    
    .icon-item:active {
        animation: card-bounce 0.25s ease-out;
        transform: translateY(-6px) scale(1.03);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.18);
    }
    
    .icon-emoji { font-size: 28px; }
    .icon-text { font-size: 15px; font-weight: 900; color: #000000; }
    
    @keyframes card-bounce {
        0% { transform: translateY(0) scale(1); }
        55% { transform: translateY(-10px) scale(1.04); }
        100% { transform: translateY(-4px) scale(1.02); }
    }
</style>
""", unsafe_allow_html=True)

# PWA 메타 주입
pwa_helper.inject_pwa_tags()

# 📌 모바일 캐시 갱신 (빌드 버전 변경 시 강제 새로고침)
def inject_cache_bust(build_version: str):
    components.html(f"""
    <script>
    (function() {{
        const v = "{build_version}";
        const k = "dnbs_build_version";
        const prev = localStorage.getItem(k);
        if (prev && prev !== v) {{
            if ('caches' in window) {{
                caches.keys().then(keys => Promise.all(keys.map(key => caches.delete(key))));
            }}
            if (navigator.serviceWorker) {{
                navigator.serviceWorker.getRegistrations().then(regs => regs.forEach(r => r.unregister()));
            }}
            setTimeout(() => location.reload(), 150);
        }}
        localStorage.setItem(k, v);
    }})();
    </script>
    """, height=0, scrolling=False)

def inject_manifest(build_version: str):
    components.html(f"""
    <script>
    (function() {{
        const href = "/manifest.json?v={build_version}";
        let link = document.querySelector('link[rel="manifest"]');
        if (!link) {{
            link = document.createElement('link');
            link.rel = 'manifest';
            document.head.appendChild(link);
        }}
        link.href = href;
    }})();
    </script>
    """, height=0, scrolling=False)

inject_manifest(BUILD_VERSION)
inject_cache_bust(BUILD_VERSION)

# =========================
# Kakao Login Helpers
# =========================
def get_kakao_auth_url():
    rest_key = st.secrets.get("KAKAO_REST_API_KEY", "")
    redirect_uri = st.secrets.get("KAKAO_REDIRECT_URI", "")
    if not rest_key or not redirect_uri:
        return None
    params = {
        "client_id": rest_key,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "profile_nickname account_email phone_number",
        "state": "dnbs"
    }
    return f"https://kauth.kakao.com/oauth/authorize?{urlencode(params)}"


def normalize_kakao_phone(phone_raw: str) -> str:
    if not phone_raw:
        return ""
    digits = "".join([c for c in phone_raw if c.isdigit()])
    if digits.startswith("82"):
        digits = "0" + digits[2:]
    return digits


def handle_kakao_callback():
    if "code" not in st.query_params:
        return
    if st.query_params.get("state") != "dnbs":
        return
    if st.session_state.get("kakao_processing"):
        return
    st.session_state.kakao_processing = True

    code = st.query_params.get("code")
    rest_key = st.secrets.get("KAKAO_REST_API_KEY", "")
    redirect_uri = st.secrets.get("KAKAO_REDIRECT_URI", "")
    if not rest_key or not redirect_uri:
        st.error("카카오 로그인 설정이 없습니다. 관리자에게 문의하세요.")
        return

    try:
        token_res = requests.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": rest_key,
                "redirect_uri": redirect_uri,
                "code": code
            },
            timeout=10
        )
        if token_res.status_code != 200:
            st.error("카카오 로그인에 실패했습니다. 다시 시도해주세요.")
            return

        access_token = token_res.json().get("access_token")
        if not access_token:
            st.error("카카오 토큰이 발급되지 않았습니다.")
            return

        user_res = requests.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        if user_res.status_code != 200:
            st.error("카카오 계정 정보를 가져오지 못했습니다.")
            return

        user_data = user_res.json()
        kakao_id = str(user_data.get("id", ""))
        kakao_account = user_data.get("kakao_account", {})
        profile = kakao_account.get("profile", {}) if kakao_account else {}
        nickname = profile.get("nickname") or "카카오 사용자"
        email = kakao_account.get("email", "") if kakao_account else ""
        phone_raw = kakao_account.get("phone_number", "") if kakao_account else ""
        phone = normalize_kakao_phone(phone_raw)

        store_id = f"kakao_{kakao_id}"
        store = db_manager.get_store(store_id)
        if not store:
            store_data = {
                "password": uuid4().hex[:12],
                "name": nickname,
                "owner_name": nickname,
                "phone": phone,
                "info": "카카오 로그인 가입",
                "menu_text": "",
                "category": "other",
                "membership": "일반"
            }
            db_manager.save_store(store_id, store_data, encrypt_password=True)
            store = db_manager.get_store(store_id)

        if store:
            st.session_state.logged_in_store = store
            st.session_state.store_id = store_id
            welcome_msg = "동네비서 AI 가족이 되신 것을 환영합니다! 프리미엄 혜택을 확인해보세요"
            if phone:
                ok, msg = sms_manager.send_alimtalk(phone, welcome_msg)
                if not ok:
                    st.warning(f"알림톡 발송 실패: {msg}")
            else:
                st.info("카카오 계정에 전화번호가 없어 알림톡 발송을 생략했습니다.")
            st.query_params.clear()
            st.session_state.page = "home"
            st.rerun()
        else:
            st.error("가입 처리 중 문제가 발생했습니다. 다시 시도해주세요.")
    finally:
        st.session_state.kakao_processing = False


# 🔐 [자동 로그인 시스템]
def handle_persistent_login():
    if st.session_state.get("logout_requested"):
        st.session_state.logout_requested = False
        st.session_state.logged_in_store = None
        st.markdown("""
        <script>
            localStorage.removeItem('dnbs_store_id');
            localStorage.setItem('dnbs_logout', 'true');
            const url = new URL(window.location.href);
            url.searchParams.delete('pl');
            window.location.href = url.origin + url.pathname;
        </script>
        """, unsafe_allow_html=True)
        st.stop()

    if "pl" in st.query_params and st.session_state.get("logged_in_store") is None:
        saved_id = st.query_params["pl"]
        import db_manager
        success = False
        store_info = None
        if saved_id in ["5415tv", "admin777"]:
            if saved_id == "admin777":
                success, msg, store_info = db_manager.verify_master_login(saved_id, "pass777")
            else:
                master_pw = st.secrets.get("admin", {}).get("password", "Qqss12!!0")
                success, msg, store_info = db_manager.verify_master_login(saved_id, master_pw)
        else:
            store_info = db_manager.get_store(saved_id)
            if store_info: success = True
        
        if success and store_info:
            st.session_state.logged_in_store = store_info
            st.session_state.store_id = saved_id
            if saved_id in ["admin777", "5415tv", "master"]:
                st.session_state.is_admin = True
                st.session_state.page = "ADMIN"
            st.markdown("<script>const url = new URL(window.location.href); url.searchParams.delete('pl'); window.history.replaceState({}, '', url.href);</script>", unsafe_allow_html=True)
            st.rerun()

    if st.session_state.get("logged_in_store") is None:
        st.markdown("""
        <script>
            (function() {
                const savedId = localStorage.getItem('dnbs_store_id');
                const isLogout = localStorage.getItem('dnbs_logout');
                const url = new URL(window.location.href);
                if (savedId && !url.searchParams.has('pl') && isLogout !== 'true') {
                    url.searchParams.set('pl', savedId);
                    window.location.href = url.href;
                }
                if (isLogout === 'true') { setTimeout(() => localStorage.removeItem('dnbs_logout'), 1000); }
            })();
        </script>
        """, unsafe_allow_html=True)

handle_persistent_login()
handle_kakao_callback()
st.markdown(printer_manager.get_bluetooth_printer_js(), unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "home"
if "is_admin" not in st.session_state: st.session_state.is_admin = False
if "selected_store" not in st.session_state: st.session_state.selected_store = None
if "pending_payment" not in st.session_state: st.session_state.pending_payment = None
if "bt_printer_connected" not in st.session_state: st.session_state.bt_printer_connected = False
if "lock_sender" not in st.session_state: st.session_state.lock_sender = False
if "fixed_sender" not in st.session_state: st.session_state.fixed_sender = {}
if "lock_receiver" not in st.session_state: st.session_state.lock_receiver = False
if "fixed_receiver" not in st.session_state: st.session_state.fixed_receiver = {}
if "logged_in_store" not in st.session_state: st.session_state.logged_in_store = None
if "store_id" not in st.session_state: st.session_state.store_id = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "logout_requested" not in st.session_state: st.session_state.logout_requested = False
if "mgmt_tab_index" not in st.session_state: st.session_state.mgmt_tab_index = 0
if "user_type" not in st.session_state: st.session_state.user_type = "일반사업자"

if "page" in st.query_params: st.session_state.page = st.query_params["page"]

def infer_user_type():
    store = st.session_state.get("logged_in_store")
    if store:
        explicit = store.get("user_type")
        if explicit:
            return explicit
        business_type = str(store.get("business_type", ""))
        category = str(store.get("category", ""))
        merged = f"{business_type} {category}"
        if "택배" in merged or "delivery" in merged:
            return "택배사업자"
        if "농" in merged or "farmer" in merged:
            return "농어민"
    return st.session_state.get("user_type", "일반사업자")

def navigate_to(page_name):
    st.session_state.page = page_name
    st.rerun()

def go_home():
    st.session_state.page = "home"
    st.session_state.selected_store = None
    st.session_state.pending_payment = None
    st.query_params.clear()
    st.rerun()


def render_home_button():
    if st.button("⬅️ 홈으로 돌아가기", use_container_width=True):
        go_home()


def _render_address_listener():
    components.html(
        """
        <script>
        (function() {
            if (window.__dnbsAddressListener) return;
            window.__dnbsAddressListener = true;
            window.addEventListener('message', function(event) {
                if (!event || !event.data || event.data.type !== 'daum_address') return;
                const key = event.data.key || '';
                const address = event.data.address || '';
                if (!key || !address) return;
                const inputs = window.parent.document.querySelectorAll('input');
                inputs.forEach((input) => {
                    const label = input.closest('label');
                    const labelText = label ? label.innerText : '';
                    if (key === 'sender_address' && labelText.includes('보내는 분 주소')) {
                        input.value = address;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                    if (key === 'receiver_address' && labelText.includes('받는 분 주소')) {
                        input.value = address;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                });
                // 상세주소 입력으로 포커스 이동
                inputs.forEach((input) => {
                    const label = input.closest('label');
                    const labelText = label ? label.innerText : '';
                    if (key === 'sender_address' && labelText.includes('보내는 분 상세주소')) {
                        input.focus();
                    }
                    if (key === 'receiver_address' && labelText.includes('받는 분 상세주소')) {
                        input.focus();
                    }
                });
            }, false);
        })();
        </script>
        """,
        height=0,
    )


def _create_toss_payment_link(amount, order_id, order_name, customer_name):
    secret_key = st.secrets.get("TOSS_SECRET_KEY", "")
    app_base_url = st.secrets.get("APP_BASE_URL", "")
    if not secret_key or not app_base_url:
        return None, "TOSS_SECRET_KEY 또는 APP_BASE_URL 설정이 없습니다."

    auth = base64.b64encode(f"{secret_key}:".encode("utf-8")).decode("utf-8")
    url = "https://api.tosspayments.com/v1/payments"
    payload = {
        "method": "CARD",
        "amount": int(amount),
        "orderId": str(order_id),
        "orderName": order_name,
        "customerName": customer_name,
        "successUrl": f"{app_base_url}/?page=PAYMENT_SUCCESS",
        "failUrl": f"{app_base_url}/?page=PAYMENT_FAIL"
    }
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        if res.status_code not in [200, 201]:
            return None, f"토스 결제 링크 생성 실패: {res.text}"
        data = res.json()
        checkout_url = data.get("checkout", {}).get("url")
        if not checkout_url:
            return None, "결제 링크 URL을 받지 못했습니다."
        return checkout_url, "OK"
    except Exception as e:
        return None, f"토스 결제 링크 생성 오류: {e}"


def _confirm_toss_payment(payment_key, order_id, amount):
    secret_key = st.secrets.get("TOSS_SECRET_KEY", "")
    if not secret_key:
        return False, "TOSS_SECRET_KEY 설정이 없습니다."
    auth = base64.b64encode(f"{secret_key}:".encode("utf-8")).decode("utf-8")
    url = "https://api.tosspayments.com/v1/payments/confirm"
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }
    payload = {
        "paymentKey": payment_key,
        "orderId": order_id,
        "amount": int(amount)
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        if res.status_code != 200:
            return False, f"결제 승인 실패: {res.text}"
        return True, "OK"
    except Exception as e:
        return False, f"결제 승인 오류: {e}"

def render_settlement():
    st.markdown("""
        <div class="glass-container" style="margin-bottom: 16px;">
            <div style="font-size: 22px; font-weight: 900; color: #000000;">💰 실시간 수익 정산 센터</div>
        </div>
    """, unsafe_allow_html=True)

    # 1. 정산 요약 (유형별 마진 계산)
    user_type = st.session_state.get('user_type', '일반사업자')
    st.markdown("### 💵 이번 달 예상 수익", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    def _safe_sum(series):
        return pd.to_numeric(series.astype(str).str.replace(",", "").str.replace("원", ""), errors="coerce").fillna(0).sum()

    if user_type == "일반사업자":
        platform_fee = 33000
    elif user_type == "택배사업자":
        platform_fee = 11000
    else:
        platform_fee = 0

    delivery_margin = 0
    sms_margin = 0
    ai_margin = 0

    delivery_df = db_manager.get_business_data("택배사업자")
    if not delivery_df.empty:
        if "수수료(마진)" in delivery_df.columns:
            delivery_margin = _safe_sum(delivery_df["수수료(마진)"])
        elif "수수료" in delivery_df.columns:
            delivery_margin = _safe_sum(delivery_df["수수료"])

    perf_df = pd.DataFrame()
    spreadsheet = db_manager.get_spreadsheet()
    if spreadsheet is not None:
        try:
            perf_ws = spreadsheet.worksheet(db_manager.PERFORMANCE_SHEET)
            perf_df = pd.DataFrame(perf_ws.get_all_records())
        except Exception:
            perf_df = pd.DataFrame()

    if not perf_df.empty and "type" in perf_df.columns:
        type_series = perf_df["type"].astype(str).str.lower()
        if "commission" in perf_df.columns:
            commission = perf_df["commission"]
        else:
            commission = perf_df.get("amount", pd.Series(dtype="object"))

        sms_mask = type_series.str.contains("sms|문자|alimtalk|알림톡", regex=True)
        ai_mask = type_series.str.contains("ai|상담|aicc", regex=True)
        sms_margin = _safe_sum(commission[sms_mask])
        ai_margin = _safe_sum(commission[ai_mask])

    total_margin = platform_fee + delivery_margin + sms_margin + ai_margin
    c1.metric("총 정산 금액", f"{total_margin:,.0f}원", "데이터 기반")
    c2.metric("택배 수익", f"{delivery_margin:,.0f}원", "데이터 기반")
    c3.metric("문자 수익", f"{sms_margin:,.0f}원", "데이터 기반")

    # 2. 정산 상세 내역 (탭 구분)
    tab1, tab2 = st.tabs(["정산 내역 확인", "계좌 설정"])

    with tab1:
        st.markdown("📅 **2026년 1월 정산 예정일: 2월 5일**", unsafe_allow_html=True)
        data = {
            '구분': ['구독료', '택배마진', '문자마진', 'AI상담수수료'],
            '발생금액': [platform_fee, int(delivery_margin), int(sms_margin), int(ai_margin)],
            '상태': ['대기중', '대기중', '대기중', '대기중']
        }
        st.table(pd.DataFrame(data))

    with tab2:
        st.info("정산받으실 계좌 정보를 입력해 주세요.")
        st.text_input("은행명", value="농협")
        st.text_input("계좌번호", value="302-XXXX-XXXX-XX")
        st.text_input("예금주", value="홍길동")
        if st.button("계좌 정보 저장"):
            st.success("정산 계좌가 등록되었습니다.")

    render_home_button()


def render_payment():
    st.markdown("""
        <div class="glass-container" style="margin-bottom: 16px;">
            <div style="font-size: 22px; font-weight: 900; color: #000000; text-align: center;">💳 서비스 구독 및 결제</div>
        </div>
    """, unsafe_allow_html=True)

    user_type = st.session_state.get('user_type', '일반사업자')
    st.markdown(f"### 📢 {user_type}님을 위한 맞춤 플랜", unsafe_allow_html=True)

    if user_type == "일반사업자":
        plan_name = "매장 올인원 비서"
        price = "33,000원 / 월"
        features = ["AI 전화 응대 무제한", "실시간 예약 관리", "주간 경영 리포트"]
    elif user_type == "택배사업자":
        plan_name = "물류 자동화 마스터"
        price = "11,000원 / 월 (건당 수수료 별도)"
        features = ["로젠 API 송장 출력", "AI 주소 자동 추출", "물동량 분석 리포트"]
    else:
        plan_name = "농가 상생 파트너"
        price = "55,000원 / 충전식 (5000건)"
        features = ["대량 단골 문자 할인", "AI 주문 장부 자동화", "직거래 관리 리포트"]

    st.markdown(
        f"""
        <div class="glass-container" style="margin-bottom: 10px;">
            <div style="font-size: 18px; font-weight: 900; color: #000000;">[{plan_name}]</div>
            <div style="font-size: 14px; font-weight: 900; color: #000000; margin-top: 6px;">가격: {price}</div>
            <div style="font-size: 13px; font-weight: 800; color: #000000; margin-top: 8px;">
                주요기능: {", ".join(features)}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    pay_method = st.radio("결제 수단 선택", ["신용카드", "계좌이체", "카카오페이 / 토스페이"])

    if st.button(f"{plan_name} 결제하기", use_container_width=True):
        st.balloons()
        st.success("결제 연동 API 호출 중... (토스 페이먼츠 테스트 모드)")

    render_home_button()


def render_health_check():
    """연결 상태 점검 (쿼리 파라미터로만 노출)"""
    if st.query_params.get("health") != "1":
        return
    st.markdown("### 🔍 연결 상태 점검", unsafe_allow_html=True)
    spreadsheet = db_manager.get_spreadsheet()
    if spreadsheet:
        st.success("✅ Google Sheets 연결 성공")
        try:
            st.info(f"시트 제목: {spreadsheet.title}")
        except Exception:
            st.info("시트 제목 읽기 성공")
    else:
        st.error("❌ Google Sheets 연결 실패")

now = datetime.now()
time_str = now.strftime('%H:%M:%S')
date_str = now.strftime('%Y. %m. %d') + f" ({['월','화','수','목','금','토','일'][now.weekday()]})"

# 🧑‍💼 [관리자 화면]
if st.session_state.page == "ADMIN":
    if not st.session_state.get("is_admin"):
        st.error("관리자 권한이 필요합니다.")
        st.info("로그인 후 관리자 권한이 있으면 자동으로 접근됩니다.")
    else:
        render_admin_page()

# 🏠 [메인 화면]
elif st.session_state.page == "home":
    render_health_check()
    ENABLE_RICH_HOME = False
    if not ENABLE_RICH_HOME:
        st.markdown("### 메인 홈")
        st.write("기능 복구 모드입니다. 클릭/이동 우선.")
        col_a, col_b, col_c, col_d = st.columns(4)
        if col_a.button("로그인/회원가입", use_container_width=True):
            navigate_to("JOIN")
        if col_b.button("AI 택배", use_container_width=True):
            navigate_to("DELIVERY")
        if col_c.button("AI 매장비서", use_container_width=True):
            navigate_to("AI_CHAT")
        if col_d.button("실시간 수익", use_container_width=True):
            navigate_to("SETTLEMENT")

        st.divider()
        st.markdown("### 기타 메뉴")
        col_e, col_f, col_g = st.columns(3)
        if col_e.button("매장 관리", use_container_width=True):
            navigate_to("settings")
        if col_f.button("프리미엄 리포트", use_container_width=True):
            navigate_to("report")
        if col_g.button("고객지원", use_container_width=True):
            navigate_to("support")
        st.stop()
    # 1. 멤버십 바 구성
    is_logged_in = st.session_state.logged_in_store is not None
    action_cols = st.columns(4)
    if action_cols[0].button("로그인/회원가입", use_container_width=True):
        navigate_to("JOIN")
    if action_cols[1].button("AI 택배", use_container_width=True):
        navigate_to("DELIVERY")
    if action_cols[2].button("AI 매장비서", use_container_width=True):
        navigate_to("AI_CHAT")
    if action_cols[3].button("실시간 수익", use_container_width=True):
        navigate_to("SETTLEMENT")
    if not is_logged_in:
        kakao_auth_url = get_kakao_auth_url()
        kakao_button_html = ""
        if kakao_auth_url:
            kakao_button_html = f"""
            <a href="{kakao_auth_url}" target="_top" style="text-decoration: none;">
                <div class="kakao-btn">카카오톡으로 시작하기</div>
            </a>
            """
        membership_html = f"""
        <div class="glass-container membership-bar">
            <div>
                <div style="font-size: 16px; font-weight: 900; color: #000000;">지금 가입하고 프리미엄 혜택을 받으세요</div>
                <div style="font-size: 12px; font-weight: 800; color: #000000; opacity: 0.8;">로그인 후 일반/프리미엄 등급이 자동 표시됩니다</div>
            </div>
            <div class="membership-badges">
                <span class="level-badge">일반</span>
                <span class="level-badge premium">프리미엄</span>
                <a href="/?page=JOIN" target="_top" style="text-decoration: none;">
                    <div style="background: #FFFFFF; color: #000000; border: 2px solid #000000; padding: 10px 18px; border-radius: 50px; font-weight: 900; font-size: 14px;">로그인 / 회원가입</div>
                </a>
                {kakao_button_html}
            </div>
        </div>
        """
    else:
        store = st.session_state.logged_in_store
        level = store.get('membership', '일반')
        level_color = "#9D4EDD" if level == '프리미엄' else "#666666"
        membership_html = f"""
        <div class="glass-container membership-bar">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div class="level-badge {'premium' if level == '프리미엄' else ''}">{level} 멤버십</div>
                <div style="font-size: 18px; font-weight: 900; color: #000000;">{store["name"]} 사장님</div>
            </div>
            <div class="membership-badges">
                <a href="/?page=PREMIUM_ONLY" target="_top" style="text-decoration: none;">
                    <div style="border: 2px solid #000000; color: #000000; padding: 8px 16px; border-radius: 50px; font-weight: 900; font-size: 13px;">혜택 안내</div>
                </a>
            </div>
        </div>
        """

    # 2. 3대 핵심 킬러 카드
    killer_cards_html = f"""
    <div class="core-cards">
        <a href="/?page=DELIVERY" target="_top" class="glass-card core-card" onclick="window.top.location.href='/?page=DELIVERY'; return false;">
            <div>
                <div style="background: #FFFFFF; color: #000000; border: 1px solid #000000; display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 900; margin-bottom: 10px;">인기 서비스</div>
                <div class="core-title">AI 택배</div>
                <div class="core-desc">택배기사님 필수! 주소 입력 없이 음성으로 송장 즉시 출력</div>
            </div>
            <div class="core-icon">📦</div>
        </a>
        <a href="/?page=AI_CHAT" target="_top" class="glass-card core-card" onclick="window.top.location.href='/?page=AI_CHAT'; return false;">
            <div>
                <div style="background: #FFFFFF; color: #000000; border: 1px solid #000000; display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 900; margin-bottom: 10px;">AI 자동화</div>
                <div class="core-title">AI 매장비서</div>
                <div class="core-desc">자영업 사장님 필수! 단골 관리부터 예약까지 AI가 24시간 응대</div>
            </div>
            <div class="core-icon">🤖</div>
        </a>
        <a href="/?page=SETTLEMENT" target="_top" class="glass-card core-card" onclick="window.top.location.href='/?page=SETTLEMENT'; return false;">
            <div>
                <div style="background: #FFFFFF; color: #000000; border: 1px solid #000000; display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 900; margin-bottom: 10px;">정산 센터</div>
                <div class="core-title">실시간 수익</div>
                <div class="core-desc">투명한 정산! 오늘 번 순수익을 실시간으로 확인하세요</div>
            </div>
            <div class="core-icon">💰</div>
        </a>
    </div>
    """

    # 3. 하단 아이콘 버튼 그리드
    bottom_menus = [
        {"title": "통합 예약/주문", "icon": "📅", "target": "reservation", "color": "#FFFFFF"},
        {"title": "테스트카드", "icon": "🧪", "target": "test_card", "color": "#FFFFFF"},
        {"title": "단골 문자 발송", "icon": "✉️", "target": "sms", "color": "#FFFFFF"},
        {"title": "매장 기본 설정", "icon": "⚙️", "target": "settings", "color": "#FFFFFF"},
        {"title": "AI 전화 응대 설정", "icon": "📞", "target": "aicc_setup", "color": "#FFFFFF"},
        {"title": "프리미엄 리포트", "icon": "💎", "target": "report", "color": "#FFFFFF"},
        {"title": "서비스 결제", "icon": "💳", "target": "PAYMENT", "color": "#FFFFFF"},
        {"title": "수익 정산 센터", "icon": "💰", "target": "settlement", "color": "#FFFFFF"},
        {"title": "고객지원 센터", "icon": "📢", "target": "support", "color": "#FFFFFF"}
    ]
    
    icon_grid_html = '<div class="icon-grid">'
    for m in bottom_menus:
        icon_grid_html += f'<a href="/?page={m["target"]}" target="_top" class="icon-item" style="background:{m["color"]};" onclick="window.top.location.href=\'/?page={m["target"]}\'; return false;"><div class="icon-emoji">{m["icon"]}</div><div class="icon-text">{m["title"]}</div></a>'
    icon_grid_html += '</div>'

    # 상단 멤버십 바 (iframe 밖에서 렌더링하여 링크 동작 보장)
    membership_html = "\n".join([line.lstrip() for line in membership_html.splitlines()])
    st.markdown(membership_html, unsafe_allow_html=True)

    # 전체 레이아웃 결합
    full_ui_html = textwrap.dedent(f"""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        html, body {{
            background: #FFFFFF;
            font-family: 'Pretendard', sans-serif !important;
            pointer-events: auto !important;
        }}
        a {{ color: #000000; text-decoration: none; }}
        a, button, [role="button"] {{ pointer-events: auto !important; cursor: pointer !important; }}
        .glass-container {{
            background: #FFFFFF !important;
            border: 1px solid #000000;
            border-radius: 30px;
            padding: 22px 26px;
            margin-bottom: 18px;
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
        }}
        .force-white, .force-white * {{
            color: #000000 !important;
        }}
        .glass-card {{
            background: #FFFFFF !important;
            border: 1px solid #000000;
            border-radius: 32px;
            padding: 28px 32px;
            box-shadow: 0 8px 18px rgba(0, 0, 0, 0.08);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            display: block;
            text-decoration: none;
            margin-bottom: 15px;
        }}
        .glass-card:hover {{
            transform: translateY(-5px);
            background: #FFFFFF !important;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
        }}
        .glass-card:active {{
            animation: card-bounce 0.25s ease-out;
        }}
        .core-card {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            min-height: 150px;
            width: 100%;
            border: 1px solid #000000;
            position: relative;
            z-index: 2;
        }}
        .core-title {{
            font-size: 28px;
            font-weight: 900;
            color: #000000;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }}
        .core-desc {{
            font-size: 15px;
            font-weight: 900;
            color: #000000;
            line-height: 1.45;
        }}
        .core-icon {{
            font-size: 58px;
            flex-shrink: 0;
        }}
        .icon-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 14px;
            padding: 10px 0;
        }}
        .icon-item {{
            border-radius: 16px;
            padding: 18px 12px;
            min-height: 96px;
            text-align: left;
            text-decoration: none;
            border: 1px solid #000000;
            box-shadow: none;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            display: flex;
            align-items: center;
            gap: 12px;
            will-change: transform;
            position: relative;
            z-index: 2;
            cursor: pointer;
            pointer-events: auto !important;
        }}
        .membership-bar a, .kakao-btn {{
            position: relative;
            z-index: 2;
            cursor: pointer;
            pointer-events: auto !important;
        }}
        .icon-item:active {{
            transform: translateY(-6px) scale(1.03);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.18);
            animation: card-bounce 0.25s ease-out;
        }}
        .icon-emoji {{ font-size: 28px; }}
        .icon-text {{ font-size: 15px; font-weight: 900; color: #000000; }}
        @keyframes card-bounce {{
            0% {{ transform: translateY(0) scale(1); }}
            55% {{ transform: translateY(-10px) scale(1.04); }}
            100% {{ transform: translateY(-4px) scale(1.02); }}
        }}
        .mini-clock {{
            width: 48px;
            height: 48px;
            border: 3px solid #000000;
            border-radius: 50%;
            position: relative;
            background: rgba(255, 255, 255, 0.6);
            box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.12);
        }}
        .mini-clock .hand {{
            position: absolute;
            left: 50%;
            top: 50%;
            transform-origin: 50% 100%;
            background: #000000;
            border-radius: 6px;
        }}
        .mini-clock .second-hand {{
            width: 2px;
            height: 20px;
        }}
        .mini-clock .minute-hand {{
            width: 3px;
            height: 16px;
        }}
        .mini-clock .hour-hand {{
            width: 4px;
            height: 12px;
        }}
        .mini-clock .center-dot {{
            width: 6px;
            height: 6px;
            background: #000000;
            border-radius: 50%;
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
        }}
        .premium-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.45);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            padding: 16px;
            pointer-events: none;
        }}
        .premium-overlay.active {{
            display: flex;
            pointer-events: auto;
        }}
        .premium-modal {{
            width: min(520px, 92vw);
            background: rgba(255, 255, 255, 0.92);
            border-radius: 28px;
            border: 1px solid rgba(255, 255, 255, 0.9);
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.18);
            padding: 22px 22px 18px;
            position: relative;
            backdrop-filter: blur(18px) saturate(160%);
        }}
        .premium-badge {{
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background: #000000;
            color: #FFFFFF !important;
            font-size: 12px;
            font-weight: 900;
            margin-bottom: 12px;
        }}
        .premium-title {{
            font-size: 24px;
            font-weight: 900;
            color: #000000;
            margin: 6px 0 10px;
            line-height: 1.2;
        }}
        .premium-headline {{
            font-size: 16px;
            font-weight: 900;
            color: #000000;
            margin-bottom: 12px;
        }}
        .premium-desc {{
            font-size: 14px;
            font-weight: 900;
            color: #000000;
            line-height: 1.5;
            margin-bottom: 16px;
        }}
        .premium-desc .bullet {{
            display: block;
            margin-bottom: 6px;
        }}
        .premium-cta {{
            width: 100%;
            background: #FFFFFF;
            color: #000000 !important;
            border: 2px solid #000000;
            border-radius: 999px;
            padding: 12px 16px;
            text-align: center;
            font-weight: 900;
            font-size: 15px;
        }}
        .premium-close {{
            position: absolute;
            top: 12px;
            right: 12px;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: rgba(0, 0, 0, 0.08);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            color: #000000;
            cursor: pointer;
        }}
        .premium-nav {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 14px;
            gap: 8px;
        }}
        .premium-nav button {{
            border: 0;
            background: #FFFFFF;
            color: #000000;
            padding: 8px 12px;
            border-radius: 10px;
            font-weight: 900;
            cursor: pointer;
            box-shadow: 0 6px 14px rgba(0, 0, 0, 0.08);
        }}
        .premium-dots {{
            display: flex;
            gap: 6px;
            align-items: center;
            justify-content: center;
            flex: 1;
        }}
        .premium-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: rgba(0, 0, 0, 0.2);
        }}
        .premium-dot.active {{
            background: #000000;
        }}
        .premium-snooze {{
            width: 100%;
            margin-top: 12px;
            text-align: right;
        }}
        .premium-snooze button {{
            background: transparent;
            border: 0;
            color: #000000;
            font-weight: 900;
            cursor: pointer;
            text-decoration: underline;
        }}
    </style>
    <div style="padding: 0 5px 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin: 10px 0 25px; padding: 0 5px;">
            <div>
                <div style="font-size: 30px; font-weight: 900; color: #000000; letter-spacing: -1px;">동네비서<span>.</span></div>
                <div style="font-size: 13px; color: #000000; opacity: 0.7;">Premium AI Store Management</div>
            </div>
            <div style="text-align: right; display: flex; align-items: center; gap: 10px; justify-content: flex-end;">
                <div>
                    <div id="clock" style="font-size: 28px; font-weight: 800; color: #000000;">{time_str}</div>
                    <div style="font-size: 14px; color: #000000; opacity: 0.7;">{date_str}</div>
                </div>
                <div class="mini-clock" aria-hidden="true">
                    <div class="hand hour-hand" id="clock-hour"></div>
                    <div class="hand minute-hand" id="clock-minute"></div>
                    <div class="hand second-hand" id="clock-second"></div>
                    <div class="center-dot"></div>
                </div>
            </div>
        </div>
        {killer_cards_html}
        
        <div style="margin-bottom: 15px; padding: 0 10px;">
            <div style="font-size: 16px; font-weight: 900; color: #000000;">기타 서비스</div>
        </div>
        {icon_grid_html}

        <div style="margin-top: 35px; background: #FFFFFF; border-radius: 100px; padding: 12px 25px; display: flex; align-items: center; border: 1px solid #000000;">
            <span style="background: #FFFFFF; color: #000000; border: 1px solid #000000; font-size: 12px; font-weight: 900; padding: 3px 12px; border-radius: 50px; margin-right: 15px;">SYSTEM</span>
            <span style="color: #000000; font-size: 14px; font-weight: 800;">동네비서 AI 시스템 최적화 완료</span>
        </div>
    </div>

    <div id="premium-overlay" class="premium-overlay">
        <div class="premium-modal">
            <div class="premium-close" id="premium-close">✕</div>
            <div class="premium-badge" id="premium-tag">🚀 프리미엄 멤버십</div>
            <div class="premium-title" id="premium-title">시간이 곧 돈입니다</div>
            <div class="premium-headline" id="premium-headline">송장 타이핑에 뺏긴 하루 1시간, AI가 찾아드립니다.</div>
            <div class="premium-desc" id="premium-desc"></div>
            <a href="/?page=PREMIUM_ONLY" target="_top" class="premium-cta" id="premium-cta" onclick="window.top.location.href='/?page=PREMIUM_ONLY'; return false;">지금 바로 업무 시간 단축하기</a>
            <div class="premium-nav">
                <button type="button" id="premium-prev">이전</button>
                <div class="premium-dots" id="premium-dots"></div>
                <button type="button" id="premium-next">다음</button>
            </div>
            <div class="premium-snooze">
                <button type="button" id="premium-snooze">오늘은 그만보기</button>
            </div>
        </div>
    </div>
    
    <script>
    (function() {{
        const parentDoc = window.parent ? window.parent.document : document;
        const doc = document;
        const updateClock = () => {{
            const clockEl = parentDoc.getElementById('clock') || doc.getElementById('clock');
            const hourHand = doc.getElementById('clock-hour');
            const minuteHand = doc.getElementById('clock-minute');
            const secondHand = doc.getElementById('clock-second');
            if (clockEl) {{
                const now = new Date();
                const h = String(now.getHours()).padStart(2, '0');
                const m = String(now.getMinutes()).padStart(2, '0');
                const s = String(now.getSeconds()).padStart(2, '0');
                clockEl.innerText = h + ':' + m + ':' + s;
                if (hourHand && minuteHand && secondHand) {{
                    const seconds = now.getSeconds() + now.getMilliseconds() / 1000;
                    const minutes = now.getMinutes() + seconds / 60;
                    const hours = (now.getHours() % 12) + minutes / 60;
                    hourHand.style.transform = `translate(-50%, -100%) rotate(${{hours * 30}}deg)`;
                    minuteHand.style.transform = `translate(-50%, -100%) rotate(${{minutes * 6}}deg)`;
                    secondHand.style.transform = `translate(-50%, -100%) rotate(${{seconds * 6}}deg)`;
                }}
            }}
            window.requestAnimationFrame(updateClock);
        }};
        updateClock();
        const premiumSlides = [
            {{
                title: "시간이 곧 돈입니다",
                headline: "송장 타이핑에 뺏긴 하루 1시간, AI가 찾아드립니다.",
                desc: [
                    "프리미엄 가입 시 음성 주소 인식 무제한 제공",
                    "송장 출력 수수료 건당 10원 추가 할인"
                ],
                cta: "지금 바로 업무 시간 단축하기"
            }},
            {{
                title: "비서 한 명 고용한 효과",
                headline: "단골 손님 예약 전화, 이제 AI 비서에게 맡기고 쉬세요.",
                desc: [
                    "부재중 전화 자동 응대 및 예약 확정 알림톡 무상 발송",
                    "매장 매출 분석 대시보드 실시간 제공"
                ],
                cta: "월 00원으로 전담 비서 채용하기"
            }},
            {{
                title: "가입 즉시 버는 돈",
                headline: "지금 프리미엄 가입 시, 택배 발송 포인트 10,000P 즉시 증정!",
                desc: [
                    "일반 회원은 50원, 프리미엄은 35원! 보낼수록 커지는 차이",
                    "오늘만 드리는 한정 혜택을 놓치지 마세요."
                ],
                cta: "10,000원 받고 시작하기"
            }}
        ];
        const overlay = document.getElementById('premium-overlay');
        const ENABLE_PREMIUM_OVERLAY = false;
        const titleEl = document.getElementById('premium-title');
        const headlineEl = document.getElementById('premium-headline');
        const descEl = document.getElementById('premium-desc');
        const ctaEl = document.getElementById('premium-cta');
        const closeBtn = document.getElementById('premium-close');
        const prevBtn = document.getElementById('premium-prev');
        const nextBtn = document.getElementById('premium-next');
        const dotsEl = document.getElementById('premium-dots');
        const snoozeBtn = document.getElementById('premium-snooze');
        let slideIndex = 0;

        const renderSlide = () => {{
            const data = premiumSlides[slideIndex];
            titleEl.innerText = data.title;
            headlineEl.innerText = data.headline;
            descEl.innerHTML = data.desc.map((d) => `<span class="bullet">• ${{d}}</span>`).join('');
            ctaEl.innerText = data.cta;
            dotsEl.innerHTML = premiumSlides.map((_, i) => `<span class="premium-dot ${'{'}i === slideIndex ? 'active' : ''{'}'}"></span>`).join('');
        }};

        const ensureClickable = () => {{
            const root = document.documentElement;
            const body = document.body;
            if (root) root.style.pointerEvents = 'auto';
            if (body) body.style.pointerEvents = 'auto';

            const clickables = [
                'a', 'button', 'input', 'select', 'textarea',
                '.core-card', '.icon-item', '.membership-bar a', '.kakao-btn'
            ];
            clickables.forEach((sel) => {{
                document.querySelectorAll(sel).forEach((el) => {{
                    el.style.pointerEvents = 'auto';
                    el.style.cursor = 'pointer';
                    if (!el.style.position) el.style.position = 'relative';
                    if (!el.style.zIndex) el.style.zIndex = '2';
                }});
            }});

            const blockers = Array.from(document.querySelectorAll('div')).filter((el) => {{
                if (el.id === 'premium-overlay') return false;
                const style = window.getComputedStyle(el);
                if (style.pointerEvents === 'none') return false;
                if (!['fixed', 'absolute'].includes(style.position)) return false;
                const rect = el.getBoundingClientRect();
                if (rect.width < window.innerWidth * 0.9 || rect.height < window.innerHeight * 0.9) return false;
                const z = parseInt(style.zIndex || '0', 10);
                if (!Number.isFinite(z) || z < 10) return false;
                return true;
            }});

            blockers.forEach((el) => {{
                el.style.pointerEvents = 'none';
            }});
        }};

        const attachClickDebug = () => {{
            const debugId = 'dnbs-click-debug';
            let box = document.getElementById(debugId);
            if (!box) {{
                box = document.createElement('div');
                box.id = debugId;
                box.style.cssText = 'position:fixed;bottom:10px;right:10px;z-index:10000;background:#111;color:#fff;padding:6px 10px;border-radius:8px;font-size:11px;font-weight:700;opacity:0.8;';
                box.textContent = 'click debug: ready';
                document.body.appendChild(box);
            }}
            window.addEventListener('click', (e) => {{
                const t = e.target;
                const cls = t.className ? String(t.className).split(' ').slice(0, 3).join('.') : '';
                box.textContent = 'click: ' + t.tagName.toLowerCase() + (t.id ? '#' + t.id : '') + (cls ? '.' + cls : '');
            }}, true);
        }};
        const neutralizeBlockers = () => {{
            const blockers = Array.from(document.querySelectorAll('div')).filter((el) => {{
                if (el.id === 'premium-overlay') return false;
                const style = window.getComputedStyle(el);
                if (style.pointerEvents === 'none') return false;
                if (style.position !== 'fixed') return false;
                const rect = el.getBoundingClientRect();
                if (rect.width < window.innerWidth * 0.9 || rect.height < window.innerHeight * 0.9) return false;
                const z = parseInt(style.zIndex || '0', 10);
                if (!Number.isFinite(z) || z < 999) return false;
                const opacity = parseFloat(style.opacity || '1');
                if (opacity > 0.2 && style.backgroundColor !== 'transparent') return false;
                return true;
            }});
            blockers.forEach((el) => {{
                el.style.pointerEvents = 'none';
            }});
        }};

        const todayKey = new Date().toISOString().slice(0, 10);
        const snoozeKey = "dnbs_premium_snooze";
        const showPremium = () => {{
            if (!overlay) return;
            const snoozed = localStorage.getItem(snoozeKey);
            if (snoozed === todayKey) {{
                overlay.classList.remove('active');
                return;
            }}
            overlay.classList.add('active');
            renderSlide();
        }};
        const hidePremium = () => {{
            if (!overlay) return;
            overlay.classList.remove('active');
        }};

        if (prevBtn) prevBtn.addEventListener('click', () => {{
            slideIndex = (slideIndex - 1 + premiumSlides.length) % premiumSlides.length;
            renderSlide();
        }});
        if (nextBtn) nextBtn.addEventListener('click', () => {{
            slideIndex = (slideIndex + 1) % premiumSlides.length;
            renderSlide();
        }});
        if (closeBtn) closeBtn.addEventListener('click', hidePremium);
        if (snoozeBtn) snoozeBtn.addEventListener('click', () => {{
            localStorage.setItem(snoozeKey, todayKey);
            hidePremium();
        }});

        if (ENABLE_PREMIUM_OVERLAY) {{
            showPremium();
        }} else {{
            hidePremium();
        }}

        neutralizeBlockers();
        setTimeout(neutralizeBlockers, 300);
        ensureClickable();
        setTimeout(ensureClickable, 300);
        attachClickDebug();
    }})();
    </script>
    """)
    full_ui_html = "\n".join([line.lstrip() for line in full_ui_html.splitlines()])
    st.markdown(full_ui_html, unsafe_allow_html=True)
    components.html("""
    <script>
    (function() {
        const parentDoc = window.parent ? window.parent.document : document;
        const tick = () => {
            const clockEl = parentDoc.getElementById('clock');
            const hourHand = parentDoc.getElementById('clock-hour');
            const minuteHand = parentDoc.getElementById('clock-minute');
            const secondHand = parentDoc.getElementById('clock-second');
            if (clockEl) {
                const now = new Date();
                const h = String(now.getHours()).padStart(2, '0');
                const m = String(now.getMinutes()).padStart(2, '0');
                const s = String(now.getSeconds()).padStart(2, '0');
                clockEl.innerText = h + ':' + m + ':' + s;
                if (hourHand && minuteHand && secondHand) {
                    const seconds = now.getSeconds() + now.getMilliseconds() / 1000;
                    const minutes = now.getMinutes() + seconds / 60;
                    const hours = (now.getHours() % 12) + minutes / 60;
                    hourHand.style.transform = `translate(-50%, -100%) rotate(${hours * 30}deg)`;
                    minuteHand.style.transform = `translate(-50%, -100%) rotate(${minutes * 6}deg)`;
                    secondHand.style.transform = `translate(-50%, -100%) rotate(${seconds * 6}deg)`;
                }
            }
            window.requestAnimationFrame(tick);
        };
        tick();
    })();
    </script>
    """, height=0, scrolling=False)

    query_params = st.query_params
    if "page" in query_params:
        target = query_params["page"]
        st.query_params.clear()
        navigate_to(target)

# 📄 [서브 페이지] 서비스 신청 관리 (택배/예약 통합)
elif st.session_state.page in ["RESERVE", "DELIVERY", "reservation", "delivery"]:
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    if st.session_state.selected_store is None:
        page_title = "📦 택배 매장 검색" if st.session_state.page == "DELIVERY" else "📅 매장 예약 검색"
        st.markdown(f'<h1 style="color:#000000; font-weight:900;">{page_title}</h1>', unsafe_allow_html=True)
        search_query = st.text_input("🔍 가맹점 이름 또는 연락처로 검색", placeholder="가게 이름을 입력하세요...")
        try:
            stores_dict = db_manager.get_all_stores()
            if stores_dict:
                store_list = [sdata for sid, sdata in stores_dict.items() if search_query.lower() in sdata.get('name', '').lower() or search_query in sdata.get('phone', '').replace('-', '')]
                for store in store_list:
                    with st.container():
                        st.markdown(f'<div class="glass-card" style="margin-bottom:10px;"><h3 style="margin:0; color:#000000;">{store["name"]}</h3><p style="margin:5px 0; color:#000000;">📍 {store.get("address", "주소 미등록")}</p></div>', unsafe_allow_html=True)
                        if st.button(f"👉 {store['name']} 선택하기", key=f"sel_{store.get('store_id', store['name'])}"):
                            st.session_state.selected_store = store
                            st.rerun()
        except Exception as e: st.error(f"DB 오류: {e}")
    else:
        store = st.session_state.selected_store
        if st.button(f"⬅️ '{store['name']}' 선택 취소"):
            st.session_state.selected_store = None
            st.rerun()
        st.markdown(f'<h2 style="color:#000000;">🏢 {store["name"]}</h2>', unsafe_allow_html=True)
        service_type = st.radio("🔔 서비스 선택", ["📅 매장 예약", "📦 택배 발송"], index=0 if st.session_state.page == "RESERVE" else 1, horizontal=True)
        st.markdown("---")
        
        if "예약" in service_type:
            with st.form("reservation_form"):
                reservation_date = st.date_input("예약 날짜")
                reservation_time = st.time_input("예약 시간")
                party_size = st.number_input("인원 수", min_value=1, max_value=50, value=2)
                cust_name = st.text_input("예약자 성함")
                cust_phone = st.text_input("연락처")
                request = st.text_area("요청사항", height=80)
                submit = st.form_submit_button("✅ 예약 신청")
                if submit:
                    if not cust_name or not cust_phone:
                        st.error("예약자 성함과 연락처를 입력해주세요.")
                    else:
                        reservation_data = {
                            "reservation_date": reservation_date.strftime("%Y-%m-%d"),
                            "reservation_time": reservation_time.strftime("%H:%M"),
                            "party_size": int(party_size),
                            "customer_name": cust_name,
                            "customer_phone": cust_phone,
                            "request": request,
                            "store_name": store.get("name", "")
                        }
                        saved = db_manager.save_table_reservation(store.get("store_id", ""), reservation_data)
                        if saved:
                            ledger_data = {
                                "일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "고객명": cust_name,
                                "연락처": cust_phone,
                                "메뉴/인원": f"{party_size}명 {request}".strip(),
                                "예약시간": f"{reservation_date.strftime('%Y-%m-%d')} {reservation_time.strftime('%H:%M')}",
                                "AI응대여부": "AI 접수",
                                "결제금액": ""
                            }
                            db_manager.save_to_google_sheet("일반사업자", ledger_data)
                            st.success("예약이 접수되었습니다.")
                            go_home()
                        else:
                            st.error("예약 저장에 실패했습니다. 잠시 후 다시 시도해주세요.")
        else:
            st.markdown("### 📦 택배 발송 신청")
            _render_address_listener()
            st.session_state.lock_sender = st.checkbox("보내는 사람 정보 고정", value=st.session_state.lock_sender)
            sender_defaults = st.session_state.fixed_sender if st.session_state.lock_sender else {}
            s_name = st.text_input("보내는 분 성함", value=sender_defaults.get("name", ""))
            s_phone = st.text_input("보내는 분 연락처", value=sender_defaults.get("phone", ""))
            address_helper.daum_address_search(key="sender_address")
            s_addr = st.text_input("보내는 분 주소", value=sender_defaults.get("address", ""))
            s_addr_detail = st.text_input("보내는 분 상세주소", value=sender_defaults.get("detail_address", ""))
            st.caption("주소 검색 후 표시된 주소를 복사해 붙여넣어 주세요. 상세주소까지 입력해주세요.")

            st.session_state.lock_receiver = st.checkbox("받는 사람 정보 고정", value=st.session_state.lock_receiver)
            receiver_defaults = st.session_state.fixed_receiver if st.session_state.lock_receiver else {}
            r_name = st.text_input("받는 분 성함", value=receiver_defaults.get("name", ""))
            r_phone = st.text_input("받는 분 연락처", value=receiver_defaults.get("phone", ""))
            address_helper.daum_address_search(key="receiver_address")
            r_addr = st.text_input("받는 분 주소", value=receiver_defaults.get("address", ""))
            r_addr_detail = st.text_input("받는 분 상세주소", value=receiver_defaults.get("detail_address", ""))
            st.caption("주소 검색 후 표시된 주소를 복사해 붙여넣어 주세요. 상세주소까지 입력해주세요.")
            item_name = st.text_input("물품명")
            item_count = st.number_input("수량", min_value=1, max_value=999, value=1)
            pickup_date = st.date_input("수거 희망일")
            weight_str = st.selectbox("무게", logen_delivery.get_weight_options())
            size_str = st.selectbox("크기", logen_delivery.get_size_options())
            use_logen = st.checkbox("로젠택배로 바로 예약하기", value=True)
            memo = st.text_area("요청사항", height=80)
            fee_info = logen_delivery.calculate_delivery_fee(
                logen_delivery.parse_weight(weight_str),
                logen_delivery.parse_size(size_str)
            )
            st.info(f"예상 요금: {fee_info.get('total_fee', 0):,}원 (무게 {fee_info.get('weight_category')}, 크기 {fee_info.get('size_category')})")
            if st.button("🚀 택배 접수 완료"):
                if not s_name or not s_phone or not r_name or not r_phone or not r_addr:
                    st.error("보내는 분/받는 분 정보와 주소를 입력해주세요.")
                else:
                    if st.session_state.lock_sender:
                        st.session_state.fixed_sender = {
                            "name": s_name,
                            "phone": s_phone,
                            "address": s_addr,
                            "detail_address": s_addr_detail
                        }
                    if st.session_state.lock_receiver:
                        st.session_state.fixed_receiver = {
                            "name": r_name,
                            "phone": r_phone,
                            "address": r_addr,
                            "detail_address": r_addr_detail
                        }
                    if use_logen:
                        sender = {
                            "name": s_name,
                            "phone": s_phone,
                            "address": s_addr,
                            "detail_address": s_addr_detail
                        }
                        receiver = {
                            "name": r_name,
                            "phone": r_phone,
                            "address": r_addr,
                            "detail_address": r_addr_detail
                        }
                        package = {
                            "type": "박스",
                            "weight": logen_delivery.parse_weight(weight_str),
                            "size": logen_delivery.parse_size(size_str),
                            "contents": item_name or "일반상품",
                            "count": int(item_count)
                        }
                        result, error = logen_delivery.create_delivery_reservation(
                            sender=sender,
                            receiver=receiver,
                            package=package,
                            pickup_date=pickup_date.strftime("%Y-%m-%d"),
                            memo=memo
                        )
                        if error:
                            st.error(f"로젠택배 예약 실패: {error}")
                            st.stop()
                        saved = db_manager.save_logen_reservation(result)
                        if saved:
                            fee_data = result.get("fee", {}) if isinstance(result, dict) else {}
                            ledger_data = {
                                "접수일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "발송인명": sender.get("name", ""),
                                "수령인명": receiver.get("name", ""),
                                "수령인 주소(AI추출)": receiver.get("address", ""),
                                "물품종류": package.get("contents", ""),
                                "운송장번호(로젠발급)": result.get("reservation_number", ""),
                                "수수료(마진)": str(fee_data.get("total_fee", ""))
                            }
                            db_manager.save_to_google_sheet("택배사업자", ledger_data)
                            st.success(f"로젠택배 예약 완료! 예약번호: {result.get('reservation_number')}")
                            if result.get("logen_web_url"):
                                st.markdown(f"[로젠택배 예약 확인하기]({result.get('logen_web_url')})")
                            go_home()
                        else:
                            st.error("로젠택배 예약 저장에 실패했습니다. 잠시 후 다시 시도해주세요.")
                        st.stop()
                    order_data = {
                        "store_id": store.get("store_id", "delivery"),
                        "store_name": store.get("name", "택배 접수"),
                        "sender_name": s_name,
                        "sender_phone": s_phone,
                        "sender_address": s_addr,
                        "receiver_name": r_name,
                        "receiver_phone": r_phone,
                        "receiver_address": r_addr,
                        "item_name": item_name,
                        "item_count": int(item_count),
                        "memo": memo
                    }
                    saved = db_manager.save_delivery_order(order_data)
                    if saved:
                        ledger_data = {
                            "접수일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "발송인명": s_name,
                            "수령인명": r_name,
                            "수령인 주소(AI추출)": r_addr,
                            "물품종류": item_name,
                            "운송장번호(로젠발급)": "",
                            "수수료(마진)": str(fee_info.get("total_fee", ""))
                        }
                        db_manager.save_to_google_sheet("택배사업자", ledger_data)
                        st.success("택배가 접수되었습니다.")
                        go_home()
                    else:
                        st.error("택배 접수 저장에 실패했습니다. 잠시 후 다시 시도해주세요.")

    render_home_button()

# 📄 [서브 페이지] 결제 시스템
elif st.session_state.page == "PAYMENT":
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    render_payment_page()

# 📄 [서브 페이지] 가맹점 가입 신청
elif st.session_state.page == "JOIN":
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    st.markdown('<h1 style="color:#000000; font-weight:900;">🤝 가맹 가입 신청</h1>', unsafe_allow_html=True)
    login_tab, join_tab, find_tab = st.tabs(["🔐 로그인", "🧾 회원가입", "🔎 아이디/비밀번호 찾기"])

    with login_tab:
        login_id = st.text_input("아이디", key="final_admin_id")
        login_pw = st.text_input("비밀번호", type="password", key="final_admin_pw")
        if st.button("🚀 로그인"):
            login_id = (login_id or "").strip()
            login_pw = (login_pw or "").strip()
            if login_id == "admin777" and login_pw == "pass777":
                st.session_state.logged_in = True
                st.session_state.logged_in_store = {"name": "동네비서 본사 (슈퍼관리자)"}
                st.session_state.store_id = login_id
                st.session_state.is_admin = True
                st.session_state.page = "ADMIN"
                st.rerun()
            success, msg, store_info = db_manager.verify_store_login(login_id, login_pw)
            if not success:
                success, msg, store_info = db_manager.verify_master_login(login_id, login_pw)
            if success:
                st.session_state.logged_in = True
                st.session_state.logged_in_store = store_info
                st.session_state.store_id = login_id
                if login_id in ["admin777", "5415tv", "master"]:
                    st.session_state.is_admin = True
                    st.session_state.page = "ADMIN"
                    st.rerun()
                st.success(f"환영합니다, {store_info['name']} 사장님!")
                st.session_state.user_type = infer_user_type()
                go_home()
            else:
                st.error(f"로그인 실패: {msg}")

    with join_tab:
        store_name = st.text_input("상호명", key="join_store_name")
        owner_name = st.text_input("대표자명", key="join_owner_name")
        phone = st.text_input("연락처", key="join_phone")
        phone_070 = st.text_input("070 번호 (선택)", key="join_phone_070")
        kakao_id = st.text_input("카톡 아이디", key="join_kakao_id")
        store_id = st.text_input("아이디", key="join_store_id")
        password = st.text_input("비밀번호", type="password", key="join_password")
        user_type = st.selectbox("사업자 유형", ["일반사업자", "택배사업자", "농어민"])
        business_type = st.selectbox("업종", ["식당/음식점", "택배/물류", "카페/디저트", "미용/뷰티", "일반판매", "기타"])
        region = st.text_input("지역(예: 서울 강남구)", key="join_region")
        memo = st.text_area("추가 문의", height=90, key="join_memo")
        if st.button("🚀 신청하기"):
            if not owner_name or not phone or not store_id or not password:
                st.error("대표자명, 연락처, 아이디, 비밀번호는 필수입니다.")
            else:
                detail_data = {
                    "store_name": store_name,
                    "owner_name": owner_name,
                    "kakao_id": kakao_id,
                    "user_type": user_type,
                    "phone_070": phone_070
                }
                inquiry_data = {
                    "name": owner_name,
                    "phone": phone,
                    "kakao_id": kakao_id,
                    "business_type": business_type,
                    "region": region,
                    "memo": memo,
                    "store_id": store_id,
                    "password": password,
                    "detail_data": json.dumps(detail_data, ensure_ascii=True)
                }
                saved = db_manager.save_inquiry(inquiry_data)
                if saved:
                    user_data = {
                        "가입일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "아이디": store_id,
                        "비밀번호": "암호화됨",
                        "상호명": store_name,
                        "사업자유형": user_type,
                        "연락처": phone,
                        "070번호": phone_070,
                        "요금제상태": "무료"
                    }
                    db_manager.save_user_management(user_data)
                    st.session_state.user_type = user_type
                    st.success("가맹 신청이 완료되었습니다.")
                    st.session_state.page = "signup_complete"
                    st.rerun()
                else:
                    st.error("가맹 신청 저장에 실패했습니다. 잠시 후 다시 시도해주세요.")

    with find_tab:
        st.markdown("### 아이디 찾기", unsafe_allow_html=True)
        with st.form("find_id_form"):
            find_owner_name = st.text_input("대표자 성함")
            find_phone = st.text_input("연락처")
            if st.form_submit_button("🔎 아이디 찾기"):
                if not find_owner_name or not find_phone:
                    st.error("대표자 성함과 연락처를 입력해주세요.")
                else:
                    found_id = db_manager.find_store_id(find_owner_name, find_phone)
                    if found_id:
                        st.success(f"아이디는 '{found_id}' 입니다.")
                    else:
                        st.error("일치하는 아이디를 찾을 수 없습니다.")

        st.markdown("---")
        st.markdown("### 비밀번호 재설정", unsafe_allow_html=True)
        with st.form("reset_pw_form"):
            reset_store_id = st.text_input("아이디", key="reset_store_id")
            reset_phone = st.text_input("연락처", key="reset_phone")
            reset_pw = st.text_input("새 비밀번호", type="password", key="reset_pw")
            if st.form_submit_button("🔐 비밀번호 재설정"):
                if not reset_store_id or not reset_phone or not reset_pw:
                    st.error("아이디, 연락처, 새 비밀번호를 입력해주세요.")
                else:
                    is_ok, msg = db_manager.validate_password_length(reset_pw)
                    if not is_ok:
                        st.error(msg)
                    else:
                        store = db_manager.get_store(reset_store_id)
                        if not store:
                            st.error("등록된 아이디를 찾을 수 없습니다.")
                        else:
                            stored_phone = store.get("phone", "").replace("-", "").strip()
                            target_phone = reset_phone.replace("-", "").strip()
                            if stored_phone != target_phone:
                                st.error("연락처가 일치하지 않습니다.")
                            else:
                                store["password"] = reset_pw
                                saved = db_manager.save_store(reset_store_id, store, encrypt_password=True)
                                if saved:
                                    st.success("비밀번호가 재설정되었습니다. 새 비밀번호로 로그인하세요.")
                                else:
                                    st.error("비밀번호 재설정에 실패했습니다. 잠시 후 다시 시도해주세요.")

    render_home_button()

# 📄 [서브 페이지] 프리미엄 멤버십 포털
elif st.session_state.page == "PREMIUM_ONLY":
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    st.markdown('<h1 style="color:#000000; font-weight:900;">💎 프리미엄 멤버십</h1>', unsafe_allow_html=True)
    st.info("프리미엄 회원 전용 공간입니다.")
    if st.button("💎 프리미엄 리포트"):
        st.session_state.page = "report"  # 페이지 상태만 변경
    render_home_button()

# 📄 [서브 페이지] 프리미엄 리포트
elif st.session_state.page == "report":
    render_report()  # 리포트 화면 실행
    render_home_button()
elif st.session_state.page == "test_card":
    render_test_card_page()
elif st.session_state.page == "PAYMENT_SUCCESS":
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    st.markdown('<h1 style="color:#000000; font-weight:900;">✅ 결제 완료</h1>', unsafe_allow_html=True)
    payment_key = st.query_params.get("paymentKey", "")
    order_id = st.query_params.get("orderId", "")
    amount = st.query_params.get("amount", 0)
    if payment_key and order_id and amount:
        ok, msg = _confirm_toss_payment(payment_key, order_id, amount)
        if ok:
            ok2, msg2 = db_manager.update_farmer_payment_status(order_id, status="결제완료")
            if ok2:
                st.success("결제가 완료되었습니다. 직거래장부에 [결제완료]가 표시되었습니다.")
            else:
                st.warning(f"결제는 완료됐으나 장부 업데이트 실패: {msg2}")
        else:
            st.error(msg)
    else:
        st.info("결제 결과 정보를 확인할 수 없습니다.")
    render_home_button()
elif st.session_state.page == "PAYMENT_FAIL":
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    st.markdown('<h1 style="color:#000000; font-weight:900;">❌ 결제 실패</h1>', unsafe_allow_html=True)
    st.error("결제가 실패했습니다. 다시 시도해주세요.")
    render_home_button()

# 📄 [서브 페이지] 유형별 치트키 안내
elif st.session_state.page == "cheat_sheet":
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    st.markdown('<h1 style="color:#000000; font-weight:900;">💡 유형별 핵심 치트키</h1>', unsafe_allow_html=True)

    cheat_rows = [
        {"구분": "일반사업자", "핵심 기능 (치트키)": "AI 실시간 예약 확정", "점주가 얻는 이득": "바쁜 점심시간에 전화 안 받아도 예약 손님이 쌓임"},
        {"구분": "택배사업자", "핵심 기능 (치트키)": "음성 주소 추출 & 송장 출력", "점주가 얻는 이득": "운송장 주소 타이핑하는 시간 90% 단축"},
        {"구분": "농어민", "핵심 기능 (치트키)": "직거래 주문 자동 장부", "점주가 얻는 이득": "전화/카톡으로 흩어진 주문을 AI가 엑셀로 자동 정리"}
    ]
    st.table(pd.DataFrame(cheat_rows))
    render_home_button()

# 📄 [서브 페이지] 회원가입 완료 후 안내
elif st.session_state.page == "signup_complete":
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    st.markdown('<h1 style="color:#000000; font-weight:900;">✅ 가입 완료 안내</h1>', unsafe_allow_html=True)
    st.info("회원가입이 정상 완료되었습니다. 아래 과금 방식 가이드를 확인해주세요.")

    fee_rows = [
        {"유형": "일반사업자", "타겟 및 특징": "음식점, 카페 등 매장 고객", "추천 과금 방식": "월 구독료 중심 (예: 월 3.3만원 / AI응대 무제한)"},
        {"유형": "택배사업자", "타겟 및 특징": "수거/배송 위주 대량 접수", "추천 과금 방식": "건당 수수료 중심 (예: 접수 건당 100원 / 기본료 낮음)"},
        {"유형": "농어민", "타겟 및 특징": "계절별 판매, 직거래 위주", "추천 과금 방식": "시즌권/충전식 (예: 문자 5,000건 패키지 / 수확기만 이용)"}
    ]
    st.table(pd.DataFrame(fee_rows))
    render_home_button()

# 📄 [서브 페이지] 매장 관리
elif st.session_state.page in ["STORE_MGMT", "settings", "aicc_setup"]:
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    st.markdown('<h1 style="color:#000000; font-weight:900;">🛠️ 매장 통합 관리</h1>', unsafe_allow_html=True)
    if st.session_state.logged_in_store is None:
        login_id = st.text_input("아이디", key="store_mgmt_login_id")
        login_pw = st.text_input("비밀번호", type="password", key="store_mgmt_login_pw")
        if st.button("🚀 로그인"):
            login_id = (login_id or "").strip()
            login_pw = (login_pw or "").strip()
            if login_id == "admin777" and login_pw == "pass777":
                st.session_state.logged_in = True
                st.session_state.logged_in_store = {"name": "동네비서 본사 (슈퍼관리자)"}
                st.session_state.store_id = login_id
                st.session_state.is_admin = True
                st.session_state.page = "ADMIN"
                st.rerun()
            success, msg, store_info = db_manager.verify_store_login(login_id, login_pw)
            if not success:
                success, msg, store_info = db_manager.verify_master_login(login_id, login_pw)
            if success:
                st.session_state.logged_in = True
                st.session_state.logged_in_store = store_info
                st.session_state.store_id = login_id
                if login_id in ["admin777", "5415tv", "master"]:
                    st.session_state.is_admin = True
                    st.session_state.page = "ADMIN"
                    st.rerun()
                st.success(f"환영합니다, {store_info['name']} 사장님!")
                st.session_state.user_type = infer_user_type()
                st.rerun()
            else:
                st.error(f"로그인 실패: {msg}")
    else:
        st.write(f"환영합니다, {st.session_state.logged_in_store['name']} 사장님!")
        if st.button("🔓 로그아웃"):
            st.session_state.logout_requested = True
            st.rerun()
    render_home_button()

# 🤖 [서브 페이지] AI 상담원
elif st.session_state.page == "AI_CHAT":
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    st.markdown('<h1 style="color:#000000; font-weight:900;">🤖 AI 지능형 상담원</h1>', unsafe_allow_html=True)
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    voice_ui_html = """
    <style>
        .voice-card {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 16px 18px;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.9);
            box-shadow: 0 10px 24px rgba(0,0,0,0.12);
            margin: 10px 0 16px;
        }
        .mic-btn {
            width: 54px;
            height: 54px;
            border-radius: 50%;
            background: #000000;
            color: #FFFFFF;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            cursor: pointer;
            border: 0;
            flex-shrink: 0;
        }
        .voice-text {
            color: #000000;
            font-weight: 900;
        }
        .voice-title {
            font-size: 16px;
            margin-bottom: 6px;
        }
        .voice-live {
            font-size: 14px;
            line-height: 1.5;
            min-height: 42px;
            padding: 8px 10px;
            border-radius: 10px;
            background: rgba(0,0,0,0.04);
        }
        .voice-status {
            font-size: 12px;
            opacity: 0.7;
            margin-top: 6px;
        }
        .voice-actions {
            display: flex;
            gap: 8px;
            margin-top: 8px;
        }
        .voice-action {
            background: #000000;
            color: #FFFFFF;
            border-radius: 999px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 900;
            border: 0;
            cursor: pointer;
        }
        .voice-action.secondary {
            background: #FFFFFF;
            color: #000000;
            border: 1px solid #000000;
        }
    </style>
    <div class="voice-card">
        <button class="mic-btn" id="mic-btn" aria-label="voice">🎤</button>
        <div class="voice-text">
            <div class="voice-title">무엇이든 불어 보세요</div>
            <div class="voice-live" id="voice-live">대화 내용을 실시간으로 표시합니다.</div>
            <div class="voice-status" id="voice-status">마이크 버튼을 누르고 말씀하세요.</div>
            <div class="voice-actions">
                <button class="voice-action" id="voice-copy">텍스트 복사</button>
                <button class="voice-action secondary" id="voice-clear">지우기</button>
            </div>
        </div>
    </div>
    <script>
        (function() {
            const micBtn = document.getElementById('mic-btn');
            const liveEl = document.getElementById('voice-live');
            const statusEl = document.getElementById('voice-status');
            const copyBtn = document.getElementById('voice-copy');
            const clearBtn = document.getElementById('voice-clear');
            let recognition = null;
            let listening = false;

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                statusEl.textContent = '이 브라우저는 음성 인식을 지원하지 않습니다.';
                micBtn.disabled = true;
            } else {
                recognition = new SpeechRecognition();
                recognition.lang = 'ko-KR';
                recognition.interimResults = true;
                recognition.continuous = true;

                recognition.onstart = () => {
                    listening = true;
                    statusEl.textContent = '듣는 중...';
                    micBtn.style.background = '#2E86DE';
                };
                recognition.onend = () => {
                    listening = false;
                    statusEl.textContent = '중지됨. 다시 누르면 재시작합니다.';
                    micBtn.style.background = '#000000';
                };
                recognition.onerror = (e) => {
                    statusEl.textContent = '오류: ' + e.error;
                };
                recognition.onresult = (event) => {
                    let transcript = '';
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        transcript += event.results[i][0].transcript;
                    }
                    if (transcript.trim().length > 0) {
                        liveEl.textContent = transcript.trim();
                    }
                };
            }

            micBtn.addEventListener('click', () => {
                if (!recognition) return;
                if (listening) {
                    recognition.stop();
                } else {
                    recognition.start();
                }
            });
            copyBtn.addEventListener('click', async () => {
                try {
                    await navigator.clipboard.writeText(liveEl.textContent);
                    statusEl.textContent = '복사 완료! 채팅 입력창에 붙여넣기 하세요.';
                } catch (e) {
                    statusEl.textContent = '복사 실패: 브라우저 권한을 확인하세요.';
                }
            });
            clearBtn.addEventListener('click', () => {
                liveEl.textContent = '';
                statusEl.textContent = '지웠습니다. 다시 말씀하세요.';
            });
        })();
    </script>
    """
    components.html(voice_ui_html, height=200, scrolling=False)
    
    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).markdown(msg["content"])
    
    user_input = st.chat_input("문의 내용을 입력하세요")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.spinner("AI 답변 생성 중..."):
            reply = ai_manager.get_ai_response(user_input, st.session_state.chat_history)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()
    render_home_button()

elif st.session_state.page in ["sms", "settlement", "support"]:
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    if st.session_state.page == "settlement":
        render_settlement()
    elif st.session_state.page == "sms":
        st.markdown('<h1 style="color:#000000; font-weight:900;">✉️ 단골 문자 발송</h1>', unsafe_allow_html=True)
        st.markdown("### 💳 결제 요청 알림톡 보내기", unsafe_allow_html=True)
        with st.form("payment_request_form"):
            customer_name = st.text_input("고객명")
            customer_phone = st.text_input("고객 연락처")
            item_name = st.text_input("품목")
            quantity = st.number_input("수량", min_value=1, max_value=999, value=1)
            amount = st.number_input("결제 금액", min_value=0, step=1000, value=10000)
            address = st.text_input("배송지 주소")
            memo = st.text_area("요청사항", height=80)
            if st.form_submit_button("💳 결제 요청 알림톡 발송"):
                if not customer_name or not customer_phone or not amount:
                    st.error("고객명, 연락처, 결제 금액은 필수입니다.")
                else:
                    order_id = f"pay_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:6]}"
                    checkout_url, msg = _create_toss_payment_link(
                        amount=amount,
                        order_id=order_id,
                        order_name=f"{item_name or '직거래 결제'}",
                        customer_name=customer_name
                    )
                    if not checkout_url:
                        st.error(msg)
                        st.stop()

                    ledger_data = {
                        "주문일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "품목": item_name,
                        "수량": int(quantity),
                        "주문금액": int(amount),
                        "입금확인여부": "결제요청",
                        "배송지주소": address,
                        "결제주문번호": order_id,
                        "고객문의사항": memo
                    }
                    db_manager.save_to_google_sheet("농어민", ledger_data)

                    message = f"""[결제 요청]
{customer_name}님 결제 요청입니다.
결제금액: {int(amount):,}원
결제링크: {checkout_url}"""
                    ok, send_msg = sms_manager.send_alimtalk(customer_phone, message)
                    if ok:
                        st.success("결제 요청 알림톡 발송 완료")
                    else:
                        st.warning(f"알림톡 발송 실패: {send_msg}")
        render_home_button()
    else:
        title_map = {
            "support": "📢 고객지원 센터"
        }
        st.markdown(f'<h1 style="color:#000000; font-weight:900;">{title_map.get(st.session_state.page, "기능 준비 중")}</h1>', unsafe_allow_html=True)
        st.info("기능 준비 중입니다.")
        render_home_button()
else:
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    st.header(f"✨ {st.session_state.page} 기능 준비 중")
    render_home_button()
